"""Create and manage automatic comments in a Github PR"""
import fileinput
import logging
import re
from os import environ
from pathlib import Path

import requests
from docopt import DocoptExit, docopt
from github import Github, GithubException
from jinja2 import Environment

try:
    from rich.logging import RichHandler
except ImportError:
    RichHandler = None

usage = """
Usage:
  pr-commenter (-h | --help)
  pr-commenter <repo> <pr> [<file>...] [--template=<template>] [--build=<build>] [--append] [--token=<token>] [--label=<label>...] [--debug]

Options:
  -h --help                     Show this screen.  
  -t, --template=<template>     Use a given Jinja template.    
  --token=<token>               Github token. Default to the envvar PR_COMMENTER_GITHUB_TOKEN.
  --label=<label>               Add label/s if there were a comment
  --build=<build>               Identifier. If a comment for the template and build exist the 
                                new message will be appended.
  --debug                       Show the final comment but don't post it to Github
"""

__version__ = "0.2.4"

logger = logging.getLogger(__file__)


def setup_logger(debug=False):
    # setup loggin
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    kw = {}
    if RichHandler:
        kw = {"handlers": [RichHandler()]}
    logging.basicConfig(format="%(message)s", datefmt="->", **kw)


def get_pr_and_user(token, repo, pr_number):
    try:
        gh = Github(token)
    except GithubException:
        raise ValueError("Token is invalid.")
    try:
        user = gh.get_user()
        pr = gh.get_repo(repo).get_pull(int(pr_number))
        return pr, user
    except (KeyError, GithubException) as e:
        raise ValueError(f"Error {type(e)}: {str(e)}")


class GraphqlClient:
    def __init__(self, token):
        self.token = token

    def _post(self, query_or_mutation, variables=None):
        response = requests.post(
            "https://api.github.com/graphql",
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
            },
            json={"query": query_or_mutation, "variables": variables},
        )
        return response.json()

    def minimize_comment(self, comment, reason="OUTDATED"):
        """
        Minimize (hide) a comment on GitHub using the api v4
        (as pygithub only cover the api rest v3 and this feature is not there)

        This will hide the comment from view, but not delete it.
        Valid reasons are: ABUSE, OFF_TOPIC, OUTDATED, RESOLVED, SPAM
        """
        mutation = """
            mutation MinimizeComment($commentId: ID!, $minimizeReason: ReportedContentClassifiers!) {
                minimizeComment(input: {subjectId: $commentId, classifier: $minimizeReason}) {
                clientMutationId
            }
        }"""
        variables = {"commentId": comment.raw_data["node_id"], "minimizeReason": reason}
        return self._post(mutation, variables)

    def is_minimized(self, comment) -> bool:
        """
        Check if a comment is minimized (hidden) on GitHub using the api v4
        """
        query = """
         query CheckMinimizedComment($commentID: ID!) {
          node(id: $commentID) {
            ... on Minimizable {
              isMinimized
            }
          }
         }
        """
        variables = {"commentID": comment.raw_data["node_id"]}
        result = self._post(query, variables)
        return result["data"]["node"]["isMinimized"]


def render(lines, template=None, build="", is_append=False):
    """
    Render the comment template passing environment variables and the lines as input_lines
    """
    if template:
        env = Environment(autoescape=False)
        t = env.from_string(Path(template).read_text())
        comment = t.render({"input_lines": lines, "is_append": is_append, **environ})
        if not is_append:
            comment = f"<!-- pr-commenter: {template} {build or ''} -->\n{comment}"
    else:
        comment = "\n".join(lines)
    logger.debug("Comment:\n%s", comment)
    return comment


def main(argv=None) -> None:
    args = docopt(__doc__ + usage, argv, version=__version__)
    debug = args["--debug"]

    setup_logger(debug)
    try:
        token = args["--token"] or environ["PR_COMMENTER_GITHUB_TOKEN"]
    except KeyError:
        raise DocoptExit("Token not found. Pass --token or set the environment variable PR_COMMENTER_GITHUB_TOKEN")

    try:
        pr, user = get_pr_and_user(token, repo=args["<repo>"], pr_number=args["<pr>"].strip("pr/"))
    except ValueError as e:
        raise DocoptExit(str(e))

    graphql_client = GraphqlClient(token)
    labels = args["--label"]
    template = args["--template"]
    build = args["--build"]
    lines = []
    files = args["<file>"]
    if files:
        with fileinput.input(files=files) as f:
            for line in f:
                lines.append(line.rstrip("\n"))

    # update or create a comment
    comment = None

    for previous_comment in pr.get_issue_comments():
        if previous_comment.user.login != user.login or graphql_client.is_minimized(previous_comment):
            # we do not consider already minimized comments
            continue

        # previous comment is a candidate to be minimized or updated
        first_line = previous_comment.body.split("\n")[0]

        match = re.search(r"<!-- pr-commenter: (\S+) (\S+)?\s*-->", first_line)
        if match:
            prev_template, prev_build = match.groups()
            if prev_template == template and prev_build != build:
                logger.info("Found a previous comment for a different build. Minimizing it...")
                if not debug:
                    graphql_client.minimize_comment(previous_comment)
                break
            elif prev_template == template and prev_build == build:
                logger.info("Found a previous comment for the same build. Appending...")
                new_comment = render(lines, template, build, is_append=True)
                comment = f"{previous_comment.body}\n{new_comment}"

                logger.debug(f"Updated comment: {comment}")
                if not debug:
                    previous_comment.edit(comment)
                    logger.info(f"Comment updated: {previous_comment.html_url}")
                break

    is_empty = False
    if not comment:
        comment = render(lines, template, args["--build"])
        is_empty = re.sub(r"<!-- pr-commenter[^>]*-->", "", comment).strip() == ""
        if is_empty:
            logger.info("New comment is empty. Skipping...")
            for label in labels:
                pr.remove_from_labels(label)
            if labels:
                logger.info(f"Labels removed: {', '.join(labels)}")
        elif not debug:
            issue_comment = pr.create_issue_comment(comment)
            logger.info(f"Comment created: {issue_comment.html_url}")
        logger.debug(f"Comment: {comment}")

    if not is_empty and labels:
        logger.info(f"Labels added: {', '.join(labels)}")
        pr.add_to_labels(*labels)


if __name__ == "__main__":
    main()
