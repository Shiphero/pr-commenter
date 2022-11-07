"""Create or upgrade a comment in a given PR"""
import os
import sys
from docopt import docopt
import fileinput
from github import Github, GithubException

usage = """
Usage:
  pr_commenter (-h | --help)
  pr_commenter <repo> <pr> <file>... [--title=<title>] [--wrap=<language>] [--token=<token>]

Options:
  -h --help                         Show this screen.  
  --title=<title>                   Title for the comment
  --wrap=<language>                 Wrap the comment as code language
  --token=<token>                   Github token. Default to the envvar PR_COMMENTER_GITHUB_TOKEN.
"""

__version__ = "0.1"

def main(argv=None) -> None:
    args = docopt(__doc__ + usage, argv, version=__version__)

    title = f"{args['--title']}\n\n" if args["--title"] else "[AUTOMATIC COMMENT]\n\n"
    comment = title
    if args["--wrap"]:
        comment += f"```{args['--wrap']}\n"

    with fileinput.input(files=args["<file>"], encoding="utf-8") as f:
        for line in f:
            comment += line
    
    if args["--wrap"]:
        comment += "\n```"


    gh = Github(args["--token"] or os.environ.get("PR_COMMENTER_GITHUB_TOKEN"))
    pr = gh.get_repo(args["<repo>"]).get_pull(int(args["<pr>"]))

    # update or create a comment
    existent_comment = None    
    for c_issue in pr.get_issue_comments():
        if c_issue.body.startswith(title):
            existent_comment = c_issue
            break
    if existent_comment:
        r = existent_comment.edit(comment)
    else:
        r = pr.create_issue_comment(comment)


if __name__ == '__main__':
    main()    
