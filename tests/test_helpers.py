from textwrap import dedent
from pr_commenter import render


def test_render(template, monkeypatch):
    monkeypatch.setenv("TITLE", "the title")
    result = render(["l1", "l2"], template, build="abc1")
    first_line, rest = result.split("\n", 1)
    assert first_line == f"<!-- pr_commenter: {template} abc1 -->"
    assert rest == """
    # Example
    the title

    ```bash
    l1
    l2
    
    ```
    """

def test_render_append(template, monkeypatch):
    monkeypatch.setenv("TITLE", "the title")
    result = render(["l1", "l2"], template, build="abc1", is_append=True)
    assert result == """
    
    the title

    ```bash
    l1
    l2
    
    ```
    """
