from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ci_and_container_delivery_files_exist() -> None:
    assert (PROJECT_ROOT / ".github" / "workflows" / "unit-test.yml").is_file()
    gitlab_config = PROJECT_ROOT / ".gitlab-ci.yml"
    assert gitlab_config.is_file()
    assert "unit-test" in gitlab_config.read_text(encoding="utf-8")
    assert (PROJECT_ROOT / "Dockerfile").is_file()


def test_ci_configs_run_the_canonical_offline_test_command() -> None:
    github_workflow = (
        PROJECT_ROOT / ".github" / "workflows" / "unit-test.yml"
    ).read_text(encoding="utf-8")
    gitlab_config = (PROJECT_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    for required_step in (
        "uses: actions/checkout@",
        "uses: actions/setup-python@",
        'python -m pip install ".[dev]"',
        "run: make test",
    ):
        assert required_step in github_workflow

    assert (
        "unit-test:\n"
        "  script:\n"
        '    - python -m pip install ".[dev]"\n'
        "    - make test"
    ) in gitlab_config


def test_dockerfile_keeps_source_tree_available_for_mock_demos() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "pip install --no-cache-dir -e ." in dockerfile
    assert 'CMD ["pyrepair", "demo", "full"]' in dockerfile


def test_dev_dependencies_include_fastapi_test_client_runtime() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]

    assert "httpx2>=0.28" in dev_dependencies


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
