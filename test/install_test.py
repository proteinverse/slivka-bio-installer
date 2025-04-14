import builtins
import contextlib
from pathlib import Path

import pytest
from hamcrest import assert_that, contains_inanyorder

from install import (
    copy_data_dirs,
    find_and_copy_data_dirs,
    find_data_dirs,
    interpolate_string,
    interpolate_list,
    interpolate_dict
)

@pytest.fixture
def suspend_capture(pytestconfig):
    capman = pytestconfig.pluginmanager.getplugin('capturemanager')

    @contextlib.contextmanager
    def _suspend_capture():
        capman.suspend_global_capture(in_=True)
        try:
            yield
        finally:
            capman.resume_global_capture()

    yield _suspend_capture()


# Test cases for the data directory matching functions

def test_find_data_dirs_default():
    data_dirs_root = Path(__file__).parent.joinpath("resources", "data_dirs")
    paths = find_data_dirs(data_dirs_root, [])
    assert_that(paths, contains_inanyorder(
        Path("data"),
        Path("external"),
        Path("notdata"),
        Path("testdata")
    ))


@pytest.mark.parametrize(
    ("include", "expected_matches"),
    [
        (
            ["*"],
            ["data", "external", "notdata", "testdata"]
        ),
        (
            ["data", "external"],
            ["data", "external"]
        ),
        (
            ["notdata"],
            ["notdata"]
        ),
        (
            ["testdata"],
            ["testdata"]
        ),
        (
            ["nonexistent"],
            []
        ),
        (
            ["data", "external", "notdata", "testdata"],
            ["data", "external", "notdata", "testdata"]
        ),
        (
            ["*data"],
            ["data", "notdata", "testdata"]
        ),
        (
            ["*tdata", "external"],
            ["external", "notdata", "testdata"]
        )
    ]
)
def test_find_data_dirs_with_include(include, expected_matches):
    data_dirs_root = Path(__file__).parent.joinpath("resources", "data_dirs")
    rules = [{'include': glob} for glob in include]
    expected_paths = [Path(path) for path in expected_matches]
    paths = find_data_dirs(data_dirs_root, rules)
    assert_that(paths, contains_inanyorder(*expected_paths))


@pytest.mark.parametrize(
    ("exclude", "expected_matches"),
    [
        (
            ["data", "external"],
            ["notdata", "testdata"]
        ),
        (
            ["notdata"],
            ["data", "external", "testdata"]
        ),
        (
            ["testdata"],
            ["data", "external", "notdata"]
        ),
        (
            ["nonexistent"],
            ["data", "external", "notdata", "testdata"]
        ),
        (
            ["data", "external", "notdata", "testdata"],
            []
        ),
        (
            ["*"],
            []
        ),
        (
            ["*data"],
            ["external"]
        ),
        (
            ["*tdata", "external"],
            ["data"]
        )
    ]
)
def test_find_data_dirs_with_exclude(exclude, expected_matches):
    data_dirs_root = Path(__file__).parent.joinpath("resources", "data_dirs")
    rules = [{'exclude': glob} for glob in exclude]
    expected_paths = [Path(path) for path in expected_matches]
    paths = find_data_dirs(data_dirs_root, rules)
    assert_that(paths, contains_inanyorder(*expected_paths))


# Test cases for the data directory copying funcitons

def test_copy_data_dirs(tmp_path):
    src_data = Path(__file__).parent.joinpath("resources", "data_dirs")
    copy_list = [
        (src_data / "data", tmp_path / "data"),
        (src_data / "testdata", tmp_path / "testdata"),
    ]
    copied = copy_data_dirs(copy_list)
    assert_that(copied, contains_inanyorder(
        (src_data / "data", tmp_path / "data"),
        (src_data / "testdata", tmp_path / "testdata"),
    ))
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "testdata").is_dir()
    assert (tmp_path / "data" / "datafile.txt").is_file()


@pytest.mark.skip(reason="Unable to read stdin in pytest")
def test_copy_data_dirs_existing_dir(tmp_path):
    src_data = Path(__file__).parent.joinpath("resources", "data_dirs")
    (tmp_path / "data").mkdir()
    copy_list = [
        (src_data / "data", tmp_path / "data"),
        (src_data / "testdata", tmp_path / "testdata"),
    ]
    copied = copy_data_dirs(copy_list)
    assert_that(copied, contains_inanyorder(
        (src_data / "testdata", tmp_path / "testdata"),
    ))
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "testdata").is_dir()


def test_find_and_copy_data_dirs(tmp_path):
    src_data = Path(__file__).parent.joinpath("resources", "data_dirs")
    patterns = [
        {"include": "data"},
        {"include": "testdata"},
    ]
    copied = find_and_copy_data_dirs(src_data, patterns, tmp_path)
    assert_that(copied, contains_inanyorder(
        (Path("data"), Path("data/data")),
        (Path("testdata"), Path("data/testdata"))
    ))
    assert (tmp_path /"data" / "data").is_dir()
    assert (tmp_path / "data" / "testdata").is_dir()

def test_find_and_copy_data_dirs_glob_pattern(tmp_path):
    src_data = Path(__file__).parent.joinpath("resources", "data_dirs")
    patterns = [
        {"include": "*data"},
    ]
    copied = find_and_copy_data_dirs(src_data, patterns, tmp_path)
    assert_that(copied, contains_inanyorder(
        (Path("data"), Path("data/data")),
        (Path("testdata"), Path("data/testdata")),
        (Path("notdata"), Path("data/notdata"))
    ))


# Test cases for the interpolation functions

@pytest.mark.parametrize(
    ("input_string", "context", "expected_output"),
    [
        ("This is a {{ key:value }}.", {"key:value": "replacement"}, "This is a replacement."),
        ("{{ local-path:HOME }}/bin.", {"local-path:HOME": "/home/slivka"}, "/home/slivka/bin."),
        ("No placeholder here.", {}, "No placeholder here."),
        pytest.param(
            "This is a {{ missing:key }}.",
            {"key:value": "replacement"},
            "This is a {{ missing:key }}.",
            marks=pytest.mark.xfail(raises=KeyError),
        )
    ]
)
def test_interpolate_string_basic(input_string, context, expected_output):
    assert interpolate_string(input_string, context) == expected_output

def test_interpolate_string_no_placeholder():
    context = {"key:value": "replacement"}
    assert interpolate_string("This is a test.", context) == "This is a test."

def test_interpolate_string_missing_key():
    context = {"key:value": "replacement"}
    with pytest.raises(KeyError):
        interpolate_string("This is a {{ missing:key }}.", context)

def test_interpolate_list_basic():
    context = {"key:value": "replacement"}
    data = ["This is a {{ key:value }}.", "No placeholder here."]
    result = interpolate_list(data, context)
    assert result == ["This is a replacement.", "No placeholder here."]

def test_interpolate_list_nested():
    context = {"key:value": "replacement", "nested:key": "nested_value"}
    data = [
        "This is a {{ key:value }}.",
        {"nested": "{{ nested:key }}"},
        ["Another {{ key:value }}."]
    ]
    result = interpolate_list(data, context)
    assert result == [
        "This is a replacement.",
        {"nested": "nested_value"},
        ["Another replacement."]
    ]

def test_interpolate_dict_basic():
    context = {"key:value": "replacement"}
    data = {"key": "This is a {{ key:value }}."}
    result = interpolate_dict(data, context)
    assert result == {"key": "This is a replacement."}

def test_interpolate_dict_nested():
    context = {"key:value": "replacement", "nested:key": "nested_value"}
    data = {
        "key": "This is a {{ key:value }}.",
        "nested": {"inner_key": "{{ nested:key }}"},
        "list": ["{{ key:value }}", {"deep_key": "{{ nested:key }}"}]
    }
    result = interpolate_dict(data, context)
    assert result == {
        "key": "This is a replacement.",
        "nested": {"inner_key": "nested_value"},
        "list": ["replacement", {"deep_key": "nested_value"}]
    }

def test_interpolate_dict_missing_key():
    context = {"key:value": "replacement"}
    data = {"key": "This is a {{ missing:key }}."}
    with pytest.raises(KeyError):
        interpolate_dict(data, context)