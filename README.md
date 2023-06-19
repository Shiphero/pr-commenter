# pr-commenter

A CLI app to manage a comment a Github PR based on content from stdin, files or environment variables. 

You can create a new comment, delete previous one of the same type
or update the "current" one. 

An special comment with metadata is added to the comment so it could be 
detected in a subsequent run and update or delete if needed. 

## Basic usage

Create a Github token with `repo` scope and export it as `PR_COMMENTER_GITHUB_TOKEN` environment variable

```
pr-commenter your/repo 12 comment.txt
```

Or from the standard input

```
cat comment.txt | pr-commenter your/repo 12 -
```

## Advanced example

Suposse you have a template `failed_tests.j2` like this

```jinja2
{% if not is_append %}## Failed tests{% endif %}
 
[suite {{ CI_SUITE_NAME }}]({{ CI_SUITE_URL }}):

```bash
{% for line in input_lines %}{{ line }}
{% endfor %}
```

And your suite produce a file `failures.txt`  with the list 
of failed tests like 

```	
tests/test_client.py::test_client_simple
tests/test_client.py::test_client_complex
```

Suppose you want to add a single comment to the PR with the failed tests for 
two different suites executions in the same "commit". 

In the post-build phase, you can run

```
$ pr-commenter your/repo $PR failures.txt -t failed_tests.j2 --build=$COMMIT
```

The first suite that finish will post a like this


````markdown
<!-- pr_commenter: failed_tests.j2 abc123 -->
## Failed tests
 
[suite client](http://the-client-url):

```bash
tests/test_client.py::test_client_simple
tests/test_client.py::test_client_complex
```
````

Then the second suite will find the previous comment for this template 
and commit (`"abc123"`, so the result will be an update like 

````markdown
<!-- pr_commenter: failed_tests.j2 abc123 -->
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

In a next commit, the first suite will post a new comment, but this time 
the commit will be different, so a new comment will be created and the previous
deleted. 

## Templates

It's use Jinja2 templates. The stdin/files is passed and a variable `input_lines`
A `is_append` will be `True` in case the new comment will be appended to an existent
one (so you can ommit some header). In addition, the complete `os.environ`
dictionary is passed, so all the environment variables are available in the template. 


## Install

- Install the package

```
pip install --user pipx
pipx install  git+ssh://git@github.com/Shiphero/pr_commenter.git
```

- Create a Github token with `repo` scope and export it as `PR_COMMENTER_GITHUB_TOKEN` environment variable



