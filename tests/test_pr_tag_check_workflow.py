from pathlib import Path

WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "pr-tag-check.yml"


def _read_step(workflow: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    step = workflow.split(marker, maxsplit=1)[1]
    return step.split("\n      - name:", maxsplit=1)[0]


def test_existing_tag_blocks_pull_request() -> None:
    """既存タグが検出された場合にPRチェックが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: タグ検出結果の公開処理と強制失敗処理が抽出されること
    Assert: GitHub Checkとworkflow jobの両方が失敗されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    publish_step = _read_step(workflow, "Publish version tag check")
    enforcement_step = _read_step(workflow, "Enforce version tag availability")

    # Assert
    assert 'let checkConclusion = "failure";' in publish_step
    assert "tagCheckCompleted && !tagExists" in publish_step
    assert "steps.tag.outputs.exists != 'false'" in enforcement_step
    assert "run: exit 1" in enforcement_step


def test_tag_lookup_failure_blocks_pull_request() -> None:
    """タグ取得に失敗した場合にPRチェックが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: タグ取得処理と結果公開処理が抽出されること
    Assert: タグ取得失敗が継続許可されずGitHub Checkも失敗されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    lookup_step = _read_step(workflow, "Check if tag exists")
    publish_step = _read_step(workflow, "Publish version tag check")

    # Assert
    assert "continue-on-error" not in lookup_step
    assert "!tagCheckCompleted" in publish_step
    assert 'let checkConclusion = "failure";' in publish_step


def test_version_read_failure_blocks_pull_request() -> None:
    """バージョン読取に失敗した場合にworkflow jobが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: バージョン読取処理が抽出されること
    Assert: バージョン読取失敗が継続許可されないこと
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    version_step = _read_step(workflow, "Read version")

    # Assert
    assert "continue-on-error" not in version_step
