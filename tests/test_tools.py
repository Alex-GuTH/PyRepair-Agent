from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pyrepair.tools import PatchApplier, ProjectScanner, PytestRunner, SafeFileReader


def test_project_scanner_separates_source_and_test_files(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text("def test_value(): pass\n", encoding="utf-8")

    result = ProjectScanner().scan(tmp_path)

    assert result == {
        "source_files": ["src/app.py"],
        "test_files": ["tests/test_app.py"],
    }


def test_pytest_runner_captures_failing_test_output(tmp_path: Path) -> None:
    test_file = tmp_path / "test_failure.py"
    test_file.write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    result = PytestRunner().run(
        tmp_path,
        [sys.executable, "-m", "pytest", "-q"],
        timeout_seconds=10,
    )

    assert result.exit_code != 0
    assert result.timed_out is False
    assert "test_failure" in result.stdout
    assert result.duration_ms >= 0


def test_pytest_runner_marks_timed_out_commands(tmp_path: Path) -> None:
    result = PytestRunner().run(
        tmp_path,
        [sys.executable, "-c", "import time; time.sleep(1)"],
        timeout_seconds=0,
    )

    assert result.timed_out is True
    assert result.exit_code != 0


def test_safe_file_reader_reads_project_file_and_rejects_path_escape(tmp_path: Path) -> None:
    file_path = tmp_path / "src" / "app.py"
    file_path.parent.mkdir()
    file_path.write_text("answer = 42\n", encoding="utf-8")

    reader = SafeFileReader()

    assert reader.read(tmp_path, "src/app.py") == "answer = 42\n"
    with pytest.raises(ValueError, match="outside project root"):
        reader.read(tmp_path, "../outside.py")


def test_patch_applier_applies_source_diff_and_rejects_path_escape(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "app.py"
    source_file.parent.mkdir()
    source_file.write_text("VALUE = 1\n", encoding="utf-8")

    patcher = PatchApplier()
    record = patcher.apply_unified_diff(
        tmp_path,
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -1 +1 @@\n"
        "-VALUE = 1\n"
        "+VALUE = 2\n",
    )

    assert record.applied is True
    assert record.files_changed == ["src/app.py"]
    assert source_file.read_text(encoding="utf-8") == "VALUE = 2\n"

    with pytest.raises(ValueError, match="outside project root"):
        patcher.apply_unified_diff(
            tmp_path,
            "--- a/src/app.py\n"
            "+++ b/../outside.py\n"
            "@@ -1 +1 @@\n"
            "-VALUE = 2\n"
            "+VALUE = 3\n",
        )


def test_patch_applier_rejects_non_source_targets(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_app.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_value():\n    assert 1 == 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="ordinary Python source"):
        PatchApplier().apply_unified_diff(
            tmp_path,
            "--- a/tests/test_app.py\n"
            "+++ b/tests/test_app.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def test_value():\n"
            "-    assert 1 == 1\n"
            "+    assert 2 == 2\n",
        )

    assert test_file.read_text(encoding="utf-8") == "def test_value():\n    assert 1 == 1\n"


@pytest.mark.parametrize(
    "target_path",
    [
        "test/helpers.py",
        "Tests/helpers.py",
        ".github/workflows/repair.py",
        "build/repair.py",
        "config/repair.py",
        "generated/repair.py",
        "Test_repair.py",
        "REPAIR_TEST.py",
    ],
)
def test_patch_applier_rejects_protected_python_paths(
    tmp_path: Path, target_path: str
) -> None:
    protected_file = tmp_path / target_path
    protected_file.parent.mkdir(parents=True, exist_ok=True)
    protected_file.write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="ordinary Python source"):
        PatchApplier().apply_unified_diff(
            tmp_path,
            f"--- a/{target_path}\n"
            f"+++ b/{target_path}\n"
            "@@ -1 +1 @@\n"
            "-VALUE = 1\n"
            "+VALUE = 2\n",
        )

    assert protected_file.read_text(encoding="utf-8") == "VALUE = 1\n"


def test_patch_applier_handles_zero_start_insertion_at_file_top(tmp_path: Path) -> None:
    source_file = tmp_path / "src" / "app.py"
    source_file.parent.mkdir()
    source_file.write_text("SECOND = 2\nTHIRD = 3\n", encoding="utf-8")

    PatchApplier().apply_unified_diff(
        tmp_path,
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "@@ -0,0 +1 @@\n"
        "+FIRST = 1\n",
    )

    assert source_file.read_text(encoding="utf-8") == "FIRST = 1\nSECOND = 2\nTHIRD = 3\n"
