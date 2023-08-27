import pytest

from pr_commenter import main, GraphqlClient

from github import PullRequest, AuthenticatedUser, PullRequestComment


@pytest.fixture
def pr_and_user(mocker):
    pull_request_mock = mocker.MagicMock(name="pull_request", autospec=PullRequest)
    user_mock = mocker.MagicMock(name="user", autospec=AuthenticatedUser, login="test_user")
    ret = (pull_request_mock, user_mock)
    mocker.patch("pr_commenter.get_pr_and_user", return_value=ret)
    return ret


@pytest.fixture(autouse=True)
def token(monkeypatch):
    monkeypatch.setenv("PR_COMMENTER_GITHUB_TOKEN", "token1")


def test_basic_from_file(tmp_path, mocker, pr_and_user, caplog):
    pr, user = pr_and_user
    comment = mocker.MagicMock(name="comment", autospec=PullRequestComment, html_url="url1")
    pr.create_issue_comment.configure_mock(return_value=comment)
    content = tmp_path / "content.txt"
    content.write_text("l1\nl2\n"),
    main(argv=["user/repo", "1", str(content)])
    pr.create_issue_comment.assert_called_once_with("l1\nl2")
    assert caplog.messages[0] == "Comment created: url1"


def test_basic_from_multi_file(tmp_path, mocker, pr_and_user, caplog):
    pr, user = pr_and_user
    comment = mocker.MagicMock(name="comment", autospec=PullRequestComment, html_url="url1")
    pr.create_issue_comment.configure_mock(return_value=comment)
    content = tmp_path / "content.txt"
    content2 = tmp_path / "content2.txt"
    content.write_text("l1\nl2\n"),
    content2.write_text("  l3\nl4\n"),  # indentation is preserved
    main(argv=["user/repo", "1", str(content), str(content2)])
    pr.create_issue_comment.assert_called_once_with("l1\nl2\n  l3\nl4")


def test_existent_comment_same_build(monkeypatch, template_simple, mocker, pr_and_user, caplog):
    minimize = mocker.patch.object(GraphqlClient, "minimize_comment")
    is_minimized = mocker.patch.object(GraphqlClient, "is_minimized", return_value=False)

    pr, user = pr_and_user

    monkeypatch.setenv("CONTENT", "new content")

    # create a previous comment
    previous_comment = mocker.MagicMock(
        name="comment",
        autospec=PullRequestComment,
        user=user,
        html_url="url_comment1",
        body=f"<!-- pr-commenter: {template_simple} abc1 -->\n    Content: original",
    )
    pr.get_issue_comments.configure_mock(return_value=[previous_comment])

    main(argv=["user/repo", "1", "--build", "abc1", "--template", template_simple])

    minimize.assert_not_called()
    is_minimized.assert_called_once_with(previous_comment)
    pr.create_issue_comment.assert_not_called()

    expected = (
        f"<!-- pr-commenter: {template_simple} abc1 -->\n    Content: original\n\n      Content: new content\n    "
    )
    previous_comment.edit.assert_called_once_with(expected)

    assert caplog.messages[0] == "Found a previous comment for the same build. Appending..."
    assert caplog.messages[1] == "Comment updated: url_comment1"


def test_with_existent_comment_other_build(monkeypatch, token, template_simple, mocker, pr_and_user, caplog):
    minimize = mocker.patch.object(GraphqlClient, "minimize_comment")
    is_minimized = mocker.patch.object(GraphqlClient, "is_minimized", return_value=False)
    pr, user = pr_and_user

    monkeypatch.setenv("CONTENT", "new content")

    # create a previous comment
    previous_comment = mocker.MagicMock(
        name="comment",
        autospec=PullRequestComment,
        user=user,
        html_url="comment1",
        body=f"<!-- pr-commenter: {template_simple} abc1 -->\n    Content: original",
    )
    pr.get_issue_comments.configure_mock(return_value=[previous_comment])
    new_comment = mocker.MagicMock(name="new_comment", autospec=PullRequestComment, html_url="new_comment_url")
    pr.create_issue_comment.configure_mock(return_value=new_comment)

    main(argv=["user/repo", "1", "--build", "xyz2", "--template", template_simple])

    # original was minimized
    is_minimized.assert_called_once_with(previous_comment)
    minimize.assert_called_once_with(previous_comment)

    previous_comment.edit.assert_not_called()

    expected = f"<!-- pr-commenter: {template_simple} xyz2 -->\n\n      Content: new content\n    "

    pr.create_issue_comment.assert_called_once_with(expected)

    assert caplog.messages[0] == "Found a previous comment for a different build. Minimizing it..."
    assert caplog.messages[1] == "Comment created: new_comment_url"


def test_empty_new_comment(mocker, pr_and_user, caplog):
    assert False
    mocker.patch("pr_commenter.render", return_value="<!-- pr-commenter: foo xyz2 -->\n")
    pr = pr_and_user[0]
    main(argv=["user/repo", "1"])
    pr.create_issue_comment.assert_not_called()
    assert caplog.messages[0] == "New comment is empty. Skipping..."


def test_empty_remove_labels(mocker, pr_and_user, caplog):
    mocker.patch("pr_commenter.render", return_value="<!-- pr-commenter: foo xyz2 -->\n")
    pr = pr_and_user[0]
    main(argv=["user/repo", "1", "--label", "foo", "--label", "bar"])
    pr.remove_from_labels.assert_has_calls([mocker.call("foo"), mocker.call("bar")])
    assert caplog.messages[1] == "Labels removed: foo, bar"


def test_not_empty_add_labels(mocker, pr_and_user, caplog):
    mocker.patch("pr_commenter.render", return_value="<!-- pr-commenter: foo xyz2 -->\ncomment")
    pr = pr_and_user[0]
    main(argv=["user/repo", "1", "--label", "foo", "--label", "bar"])
    pr.remove_from_labels.assert_not_called()
    pr.add_to_labels.assert_called_once_with("foo", "bar")
    assert caplog.messages[1] == "Labels added: foo, bar"
