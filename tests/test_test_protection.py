from src.orchestration.test_protection import detect_test_modifications, is_test_path


def test_is_test_path():
    assert is_test_path("tests/test_sample.py") is True
    assert is_test_path("tests/unit/helpers.py") is True
    assert is_test_path("src/test_utils.py") is True
    assert is_test_path("src/app.py") is False


def test_detect_test_modifications():
    paths = [
        "src/app.py",
        "tests/test_alpha.py",
        "README.md",
        "test_helper.py",
    ]
    modified = detect_test_modifications(paths)
    assert "tests/test_alpha.py" in modified
    assert "test_helper.py" in modified
    assert "src/app.py" not in modified
