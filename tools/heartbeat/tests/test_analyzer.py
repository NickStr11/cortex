from __future__ import annotations

from unittest.mock import MagicMock, patch

from beartype import beartype

from analyzer import analyze_with_claude, read_project_context


@beartype
@patch("analyzer.PROJECT_ROOT")
def test_read_project_context_exists(mock_root: MagicMock) -> None:
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "Mock Context"
    mock_root.__truediv__.return_value = mock_path

    assert read_project_context() == "Mock Context"


@beartype
@patch("analyzer.PROJECT_ROOT")
def test_read_project_context_not_found(mock_root: MagicMock) -> None:
    mock_path = MagicMock()
    mock_path.exists.return_value = False
    mock_root.__truediv__.return_value = mock_path

    assert "not found" in read_project_context()


@beartype
@patch("analyzer.read_project_context")
@patch("anthropic.Anthropic")
def test_analyze_with_claude(mock_anthropic: MagicMock, mock_read_context: MagicMock) -> None:
    mock_read_context.return_value = "Mock Project Context"

    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Mock Analysis Results")]
    mock_client.messages.create.return_value = mock_message

    result = analyze_with_claude("Raw Data")
    assert result == "Mock Analysis Results"
    mock_client.messages.create.assert_called_once()
