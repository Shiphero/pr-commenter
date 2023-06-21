import pytest

from pr_commenter import main

from github import PullRequest, AuthenticatedUser, PullRequestComment


@pytest.fixture
def pr_and_user(mocker):
    pull_request_mock = mocker.MagicMock(name='pull_request', autospec=PullRequest)
    user_mock = mocker.MagicMock(name='user', autospec=AuthenticatedUser, login='test_user')
    ret = (pull_request_mock, user_mock)
    mocker.patch('pr_commenter.get_pr_and_user', return_value=ret)
    return ret


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv("PR_COMMENTER_GITHUB_TOKEN", "token1")


def test_basic_from_file(tmp_path, mocker, pr_and_user, caplog):
    pr, user = pr_and_user
    comment = mocker.MagicMock(name='comment', autospec=PullRequestComment, html_url='url1')
    pr.create_issue_comment.configure_mock(return_value=comment)
    content = tmp_path / 'content.txt'
    content.write_text("l1\nl2\n"),
    main(argv=["user/repo", "1", str(content)])
    pr.create_issue_comment.assert_called_once_with("l1\nl2")
    assert caplog.messages[0] == "Comment created: url1"
