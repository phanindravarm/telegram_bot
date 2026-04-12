import io
from unittest.mock import patch, MagicMock
from commands.document_utils import (
    resolve_mime_type,
    extract_text_from_file,
    extract_text_from_txt,
    extract_text_from_pdf,
    extract_text_from_docx,
)


def test_resolve_mime_type_from_mime():
    assert resolve_mime_type("application/pdf", "file.pdf") == "application/pdf"
    assert resolve_mime_type("text/plain", "file.txt") == "text/plain"


def test_resolve_mime_type_from_extension():
    assert resolve_mime_type(None, "report.pdf") == "application/pdf"
    assert resolve_mime_type("", "notes.txt") == "text/plain"
    assert resolve_mime_type("", "doc.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_resolve_mime_type_unsupported():
    assert resolve_mime_type("image/png", "photo.png") is None
    assert resolve_mime_type(None, "archive.zip") is None
    assert resolve_mime_type(None, None) is None


def test_extract_text_from_txt_basic():
    content = "Hello, this is a plain text document."
    result = extract_text_from_txt(content.encode("utf-8"))
    assert result == content


def test_extract_text_from_txt_truncation():
    content = "a" * 20000
    result = extract_text_from_txt(content.encode("utf-8"), max_chars=100)
    assert len(result) == 100


def test_extract_text_from_pdf():
    """Test PDF extraction with a mocked PdfReader."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF page content here with enough text to pass minimum."

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("pypdf.PdfReader", return_value=mock_reader):
        result = extract_text_from_pdf(b"fake-pdf-bytes")

    assert "PDF page content" in result


def test_extract_text_from_docx():
    """Test DOCX extraction with a mocked Document."""
    mock_para1 = MagicMock()
    mock_para1.text = "First paragraph of the document."
    mock_para2 = MagicMock()
    mock_para2.text = "Second paragraph with more content."

    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para1, mock_para2]

    with patch("docx.Document", return_value=mock_doc):
        result = extract_text_from_docx(b"fake-docx-bytes")

    assert "First paragraph" in result
    assert "Second paragraph" in result


def test_extract_text_from_file_unsupported():
    text, error = extract_text_from_file(b"data", "image/png", "photo.png")
    assert text is None
    assert "unsupported" in error.lower()


def test_extract_text_from_file_txt():
    content = "This is enough text content to pass the minimum length check for summarization easily."
    text, error = extract_text_from_file(content.encode("utf-8"), "text/plain", "notes.txt")
    assert error is None
    assert "enough text" in text


def test_extract_text_from_file_too_short():
    text, error = extract_text_from_file(b"short", "text/plain", "notes.txt")
    assert text is None
    assert "not extract enough" in error.lower()


def test_extract_text_from_file_truncation():
    content = "a" * 20000
    text, error = extract_text_from_file(content.encode("utf-8"), "text/plain", "notes.txt", max_chars=500)
    assert error is None
    assert len(text) <= 500
