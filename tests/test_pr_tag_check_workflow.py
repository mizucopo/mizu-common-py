from pathlib import Path

WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "pr-tag-check.yml"


def _read_step(workflow: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    step = workflow.split(marker, maxsplit=1)[1]
    return step.split("\n      - name:", maxsplit=1)[0]


def test_existing_tag_blocks_pull_request() -> None:
    """既存タグが検出された場合にPRチェックが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: release version確認結果の公開処理と強制失敗処理が抽出されること
    Assert: GitHub Checkとworkflow jobの両方が失敗されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    publish_step = _read_step(workflow, "Publish version tag check")
    enforcement_step = _read_step(workflow, "Enforce version tag availability")

    # Assert
    assert 'let checkConclusion = "failure";' in publish_step
    assert "availabilityCheckCompleted && availabilityConflict" in publish_step
    assert "steps.tag-report.outputs.availability_conflict != 'false'" in (
        enforcement_step
    )
    assert "run: exit 1" in enforcement_step


def test_tag_lookup_failure_blocks_pull_request() -> None:
    """タグ取得に失敗した場合にPRチェックが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: タグ取得処理と結果集約処理が抽出されること
    Assert: タグ取得失敗が集約後にworkflow jobへ反映されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    lookup_step = _read_step(workflow, "Check if tag exists")
    report_step = _read_step(
        workflow,
        "Build release version availability summary",
    )
    enforcement_step = _read_step(workflow, "Enforce version tag availability")

    # Assert
    assert "continue-on-error: true" in lookup_step
    assert 'case "$TAG_OUTCOME:$TAG_EXISTS"' in report_step
    assert "could not be checked against git tags" in report_step
    assert "steps.tag-report.outputs.availability_check_completed != 'true'" in (
        enforcement_step
    )


def test_version_read_failure_blocks_pull_request() -> None:
    """バージョン読取に失敗した場合にworkflow jobが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: バージョン読取処理と結果集約処理が抽出されること
    Assert: バージョン読取失敗が集約後にworkflow jobへ反映されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    version_step = _read_step(workflow, "Read version")
    report_step = _read_step(
        workflow,
        "Build release version availability summary",
    )
    enforcement_step = _read_step(workflow, "Enforce version tag availability")

    # Assert
    assert "continue-on-error: true" in version_step
    assert 'if [ "$VERSION_OUTCOME" != "success" ]; then' in report_step
    assert 'AVAILABILITY_CHECK_COMPLETED="false"' in report_step
    assert "steps.tag-report.outputs.availability_check_completed != 'true'" in (
        enforcement_step
    )


def test_existing_github_release_blocks_pull_request() -> None:
    """既存GitHub Releaseが検出された場合にPRチェックが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: GitHub Release確認結果の集約処理が抽出されること
    Assert: 既存Releaseが競合としてworkflow jobへ反映されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    report_step = _read_step(
        workflow,
        "Build release version availability summary",
    )
    enforcement_step = _read_step(workflow, "Enforce version tag availability")

    # Assert
    assert 'case "$RELEASE_OUTCOME:$RELEASE_EXISTS"' in report_step
    assert "already exists as a GitHub Release" in report_step
    assert "steps.tag-report.outputs.availability_conflict != 'false'" in (
        enforcement_step
    )


def test_github_release_lookup_failure_blocks_pull_request() -> None:
    """GitHub Release確認に失敗した場合にPRチェックが失敗されること。

    Arrange: PRタグ確認workflowが読み込まれること
    Act: GitHub Release取得処理と結果集約処理が抽出されること
    Assert: Release確認失敗が集約後にworkflow jobへ反映されること
    """
    # Arrange
    workflow = WORKFLOW_PATH.read_text()

    # Act
    lookup_step = _read_step(workflow, "Check if GitHub Release exists")
    report_step = _read_step(
        workflow,
        "Build release version availability summary",
    )
    enforcement_step = _read_step(workflow, "Enforce version tag availability")

    # Assert
    assert "continue-on-error: true" in lookup_step
    assert "could not be checked against GitHub Releases" in report_step
    assert "steps.tag-report.outputs.availability_check_completed != 'true'" in (
        enforcement_step
    )
