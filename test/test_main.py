import sys
from urllib.parse import urlparse

import pytest

from feed_seeker.__main__ import main


@pytest.fixture
def run_main(monkeypatch, capsys):
    """Fixture to run main with arguments and return output."""

    def _run(*args):
        monkeypatch.setattr(sys, "argv", ["feedseeker"] + list(args))
        try:
            main()
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code

        captured = capsys.readouterr()
        return captured.out, captured.err, exit_code

    return _run


def get_domain(url):
    """Extract domain with scheme from URL."""
    return f"https://{urlparse(url).netloc}"


def parse_output_lines(output):
    """Split output into non-empty lines."""
    return [line for line in output.splitlines() if line.strip()]


def test_main_single(run_main):
    url = "https://ici.radio-canada.ca/rss"
    domain = get_domain(url)

    stdout, stderr, exit_code = run_main(url)

    assert stdout.startswith(domain)
    assert stderr == ""
    assert exit_code == 0


def test_main_all(run_main):
    url = "https://ici.radio-canada.ca/rss"
    domain = get_domain(url)
    max_links = 10

    stdout, stderr, exit_code = run_main(url, "--all", "--max-links", str(max_links))

    links = parse_output_lines(stdout)
    assert len(links) <= max_links
    for link in links:
        assert link.startswith(domain)
    assert stderr == ""
    assert exit_code == 0


def test_main_feedly(run_main):
    url = "https://ici.radio-canada.ca/rss"
    domain = get_domain(url)

    stdout, stderr, exit_code = run_main(url, "--feedly")

    links = parse_output_lines(stdout)
    assert len(links) > 0
    for link in links:
        assert link.startswith(domain)
    assert stderr == ""
    assert exit_code == 0


def test_feedly_unsupported(run_main):
    url = "https://ici.radio-canada.ca/rss"
    domain = get_domain(url)
    unsupported_args = {
        "html": "afile.html",
        "spider": 1,
        "max-time": 10,
        "all": "",
        "max-links": 10,
    }
    args = [url, "--feedly"]
    for argname, argval in unsupported_args.items():
        args.append(f"--{argname}")
        if argval != "":
            args.append(str(argval))

    stdout, stderr, exit_code = run_main(*args)

    links = parse_output_lines(stdout)
    assert len(links) > 0
    for link in links:
        assert link.startswith(domain)
    for arg in unsupported_args:
        assert arg in stderr
    assert exit_code == 0


def test_no_feed(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["feedseeker", "https://hatch.pypa.io/latest/"])

    with pytest.raises(SystemExit) as e:
        main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "No feed found\n"
    assert e.value.code == 1
