"""Helpers for reading text content out of files the user attaches."""

import base64
import io

from pydantic import BaseModel


class FileAttachment(BaseModel):
    name: str
    type: str
    data: str  # base64 data URL, e.g. "data:application/pdf;base64,...."


def extract_file_text(f: FileAttachment) -> str:
    """Decode a base64 data URL and pull out readable text, per file type."""
    try:
        raw_b64 = f.data.split(",", 1)[1] if "," in f.data else f.data
        raw_bytes = base64.b64decode(raw_b64)

        if f.type == "text/plain" or f.name.lower().endswith(".txt"):
            return raw_bytes.decode("utf-8", errors="ignore")

        if f.type == "application/pdf" or f.name.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except ImportError:
                return "[Could not read PDF: install with 'pip install pypdf']"
            reader = PdfReader(io.BytesIO(raw_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)

        if f.name.lower().endswith(".docx"):
            try:
                import docx
            except ImportError:
                return "[Could not read .docx: install with 'pip install python-docx']"
            document = docx.Document(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in document.paragraphs)

        return f"[Unsupported file type: {f.type or 'unknown'}]"
    except Exception as e:
        return f"[Could not read file {f.name}: {e}]"