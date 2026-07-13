from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ci_and_container_delivery_files_exist() -> None:
    assert (PROJECT_ROOT / ".github" / "workflows" / "unit-test.yml").is_file()
    gitlab_config = PROJECT_ROOT / ".gitlab-ci.yml"
    assert gitlab_config.is_file()
    assert "unit-test" in gitlab_config.read_text(encoding="utf-8")
    assert (PROJECT_ROOT / "Dockerfile").is_file()


def test_dockerfile_keeps_source_tree_available_for_mock_demos() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "pip install --no-cache-dir -e ." in dockerfile
    assert 'CMD ["pyrepair", "demo", "full"]' in dockerfile


def test_readme_has_required_course_headings() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    for heading in (
        "installation",
        "running cli",
        "distribution",
        "secure key configuration",
        "safety boundaries",
        "known limitations",
    ):
        assert heading in readme
