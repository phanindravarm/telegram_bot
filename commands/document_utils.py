import io
import os


SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def resolve_mime_type(mime_type, file_name):
    """Resolve mime type from Telegram-provided mime or file extension fallback."""
    if mime_type and mime_type in SUPPORTED_MIME_TYPES:
        return mime_type
    if file_name:
        ext = os.path.splitext(file_name)[1].lower()
        return EXTENSION_TO_MIME.get(ext)
    return None


def extract_text_from_pdf(file_bytes, max_chars=10000):
    """Extract text from PDF bytes."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
        if len(text) >= max_chars:
            break
    return text[:max_chars].strip()


def extract_text_from_docx(file_bytes, max_chars=10000):
    """Extract text from DOCX bytes."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
        if len(text) >= max_chars:
            break
    return text[:max_chars].strip()


def extract_text_from_txt(file_bytes, max_chars=10000):
    """Extract text from plain text bytes."""
    text = file_bytes.decode("utf-8", errors="replace")
    return text[:max_chars].strip()


def extract_text_from_file(file_bytes, mime_type, file_name, max_chars=10000):
    """Extract text from a file. Returns (text, error)."""
    resolved = resolve_mime_type(mime_type, file_name)
    if not resolved:
        return None, "Unsupported file type. Please send a PDF, TXT, or DOCX file."

    try:
        if resolved == "application/pdf":
            text = extract_text_from_pdf(file_bytes, max_chars)
        elif resolved == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_bytes, max_chars)
        elif resolved == "text/plain":
            text = extract_text_from_txt(file_bytes, max_chars)
        else:
            return None, "Unsupported file type. Please send a PDF, TXT, or DOCX file."
    except Exception as e:
        return None, f"Could not read the file: {e}"

    if not text or len(text) < 50:
        return None, "Could not extract enough text from the document."

    return text, None
