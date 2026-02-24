from __future__ import annotations

from unittest.mock import MagicMock, patch

from beartype import beartype

from main import cmd_digest, cmd_fetch, main


@beartype
@patch("main.cmd_fetch")
@patch("sys.argv", ["main.py", "--mode", "fetch"])
def test_main_fetch(mock_fetch: MagicMock) -> None:
    main()
    mock_fetch.assert_called_once()


@beartype
@patch("main.cmd_digest")
@patch("sys.argv", ["main.py", "--mode", "digest"])
def test_main_digest(mock_digest: MagicMock) -> None:
    main()
    mock_digest.assert_called_once()


@beartype
@patch("main.cmd_fetch")
@patch("sys.argv", ["main.py"])
def test_main_default(mock_fetch: MagicMock) -> None:
    main()
    mock_fetch.assert_called_once()


@beartype
@patch("formatter.format_raw_digest")
@patch("sources.fetch_all")
@patch("sys.stdout", new_callable=MagicMock)
def test_cmd_fetch(mock_stdout: MagicMock, mock_fetch_all: MagicMock, mock_format: MagicMock) -> None:
    mock_fetch_all.return_value = {"hn": [], "github": [], "reddit": [], "x": []}
    mock_format.return_value = "Mocked Raw Digest"

    cmd_fetch()

    mock_stdout.write.assert_any_call("Mocked Raw Digest")


@beartype
@patch("analyzer.analyze_with_claude")
@patch("formatter.format_raw_digest")
@patch("sources.fetch_all")
@patch("sys.stdout", new_callable=MagicMock)
def test_cmd_digest(
    mock_stdout: MagicMock, mock_fetch_all: MagicMock, mock_format: MagicMock, mock_analyze: MagicMock
) -> None:
    mock_fetch_all.return_value = {"hn": [], "github": [], "reddit": [], "x": []}
    mock_format.return_value = "Mocked Raw Digest"
    mock_analyze.return_value = "Mocked Digest Analysis"

    cmd_digest()

    mock_stdout.write.assert_any_call("Mocked Digest Analysis")
