"""Create or upgrade a comment in a given PR"""
import os
import re
from docopt import docopt
from pathlib import Path
import fileinput
from github import Github, GithubException
from os import environ
from jinja2 import Environment
import logging
from rich.logging import RichHandler


usage = """
Usage:
  pr_commenter (-h | --help)
  pr_commenter <repo> <pr> [<file>...] [--template=<template>] [--build=<build>] [--append] [--token=<token>] [--label=<label>...] [--debug]

Options:
  -h --help                     Show this screen.  
  -t, --template=<template>     Use a given Jinja template.    
  --token=<token>               Github token. Default to the envvar PR_COMMENTER_GITHUB_TOKEN.
  --label=<label>               Add label/s if there were a comment
  --build=<build>               Identifier. If a comment for the template and build exist the 
                                new message will be appended.
  --debug                       Show the final comment but don't post it to Github
"""

__version__ = "0.2"

logger = logging.getLogger(__file__)


def setup_logger(debug=False):
    # setup logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(message)s", datefmt="->", handlers=[RichHandler()]
    )
    

def get_pr_and_user(args):
    try:
        gh = Github(args["--token"] or os.environ["PR_COMMENTER_GITHUB_TOKEN"])
    except (KeyError, GithubException):
        logger.fatal("Token not found or is invalid. Pass --token or set envvar PR_COMMENTER_GITHUB_TOKEN")
        exit(1)
    try:
        user = gh.get_user().login
        pr = gh.get_repo(args["<repo>"]).get_pull(int(args["<pr>"].strip("pr/")))
        return pr, user
    except (KeyError, GithubException):
        logger.fatal("Repo or PR not found")
        exit(1)


def render(lines, template, build="", is_append=False):
    """
    Render the template passing environment variables and the lines as input_lines
    """
    env = Environment(autoescape=True)
    t = env.from_string(Path(template).read_text())
    comment = t.render({"input_lines": lines, "is_append": is_append, **environ})
    logger.debug("Comment:\n%s", comment)
    if is_append:
        return comment
    return f"<!-- pr_commenter: {template} {build or ''} -->\n{comment}"
    
    
def main(argv=None) -> None:
    args = docopt(__doc__ + usage, argv, version=__version__)
    debug = args["--debug"]

    setup_logger()

    pr, user = get_pr_and_user(args)

    lines = []
    with fileinput.input(files=args["<file>"]) as f:
        for line in f:
            lines.append(line.strip())
    
    # update or create a comment
    comment = None
    for previous_comment in pr.get_issue_comments():
        if previous_comment.user.login != user:
            # only consider comments from the same user
            continue

        first_line = previous_comment.body.split("\n")[0]

        match = re.search(r"<!-- pr_commenter: (\S+) (\S+)?\s*-->", first_line)
        if match:
            prev_template, previous_build = match.groups()
            if prev_template == args["--template"] and previous_build != args["--build"]:
                logger.info("Found a previous comment for a different build. Deleting...")
                previous_comment.delete()
                break
            elif prev_template == args["--template"] and previous_build == args["--build"]:
                logger.info("Found a previous comment for the same build. Appending...")
                new_comment = render(lines, args["--template"], args["--build"], is_append=True)
                comment = f"{previous_comment.body}\n{new_comment}"
                
                logger.debug(f"Updated comment: {comment}")
                if not debug:
                    previous_comment.edit(comment)
                    logger.info(f"Comment updated: {previous_comment.html_url}")
                break

    is_empty = False
    if not comment:
        comment = render(lines, args["--template"], args["--build"])

        is_empty = re.sub(r"<!-- pr_commenter[^>]*-->", "", comment).strip()
        if is_empty:
            logger.info("New comment is empty. Skipping...")
            # remove labels 
            for label in args["--label"]:
                logger.debug(f"Removing label: {label}")
                pr.remove_from_labels(label)
        else: 
            issue_comment = pr.create_issue_comment(comment)
            logger.debug(f"New comment: {comment}")
            logger.info(f"Comment created: {issue_comment.html_url}")

    if not is_empty and args["--label"]:        
        logger.info(f"Labels added: {', '.join(args['--label'])}")
        pr.add_to_labels(*args["--label"])


if __name__ == '__main__':
    main()    
