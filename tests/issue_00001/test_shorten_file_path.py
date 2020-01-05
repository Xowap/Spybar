from spybar.progress import shorten_file_path


def test_shorten_file_path(monkeypatch):
    monkeypatch.setenv("HOME", "/home/foo")

    assert shorten_file_path(20, "/home/foo/bar.txt") == "~/bar.txt"
    assert shorten_file_path(7, "/foo/bar/baz") == "bar/baz"
    assert shorten_file_path(10, "supermagalongname.txt") == "supe...txt"
    assert shorten_file_path(15, "supermegalongname.txt") == "supermega...txt"
    assert shorten_file_path(15, "damn.thisextension") == "damn.thisext..."
