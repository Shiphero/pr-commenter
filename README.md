# pr-commenter

Create and manage automatic comments in a Github PR

[![tests](https://github.com/Shiphero/pr-commenter/actions/workflows/pytest.yml/badge.svg?branch=main)](https://github.com/Shiphero/pr-commenter/actions/workflows/pytest.yml)
[![black](https://github.com/Shiphero/pr-commenter/actions/workflows/black.yml/badge.svg?branch=main)](https://github.com/Shiphero/pr-commenter/actions/workflows/black.yml)
[![PyPI version](https://img.shields.io/pypi/v/pr-commenter)](https://pypi.org/project/pr-commenter/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pr-commenter)](https://libraries.io/pypi/pr-commenter)


`pr-commenter` is CLI app to add a comment a Github PR based on content from stdin, files or environment variables.

You can create a new comment, hide a previous one of the same type or update the "current" one from a different process. This is done with a hidden metadata added to the comment so it could be detected in a subsequent run, and update or hide previous messages if needed.

## Basic usage

Create a Github token with `repo` scope and export it as `PR_COMMENTER_GITHUB_TOKEN` environment variable

```
pr-commenter your/repo 12 comment.txt
```

Or from the standard input, using `-` as the file name

```
cat comment.txt | pr-commenter your/repo 12 -
```

This will simply create a new comment in the PR 12 with the content of `comment.txt`
But there is much more. 


## Advanced example

Suposse you have a template `failed_tests.j2` like this

```jinja2
{% if not is_append %}## Failed tests{% endif %}
 
[suite {{ CI_SUITE_NAME }}]({{ CI_SUITE_URL }}):

```bash
{% for line in input_lines %}{{ line }}
{% endfor %}
```

Then your test-runner produces a file `failures.txt`  with the list 
of failed tests like this:

```	
tests/test_client.py::test_client_simple
tests/test_client.py::test_client_complex
```

So we want to add a **single comment** to the PR with the failed tests for 
two different suites executions triggered by the same "commit". 

In the post-build phase of both suites, you can run something like 

```bash
pr-commenter your/repo $PR failures.txt -t failed_tests.j2 --build=$COMMIT
```

The first suite that finish will post a comment like this


````markdown
<!-- pr-commenter: failed_tests.j2 abc123 -->
## Failed tests
 
[suite client](http://the-client-url):

```bash
tests/test_client.py::test_client_simple
tests/test_client.py::test_client_complex
```
````

Then the second suite will find that previous comment that was for the same 
template and same and commit (`"abc123"` in the example), so pr-commenter will
edit the comment and append the new content. 

The result will be something like this:

````markdown
<!-- pr-commenter: failed_tests.j2 abc123 -->
## Failed tests
 
[suite client](http://the-client-url):

```bash
tests/test_client.py::test_client_simple
tests/test_client.py::test_client_complex
```

[suite server](http://the-server-url):

```bash
tests/test_server.py::test_server_1
```

````

In a next commit, the first suite that finishes will post a new comment, but this time 
the commit will be different, so the previous "abc123" comment will be minimized. 

## Templates

It uses Jinja2 templates. The stdin/files is passed and a variable `input_lines`
And `is_append` will be `True` in case the new comment will be appended to an existent
one (so you can ommit the header or footer, for instance). 

In addition, the complete `os.environ` dictionary is passed, so all the environment variables are available in the template.


## Install

- Install the package with pipx

```
pip install --user pipx
pipx install pr-commenter
```

Alternatively, with pip

```
pip install --user pr-commenter
```

- Create a Github token with `repo` scope and export it as `PR_COMMENTER_GITHUB_TOKEN` environment variable



