import os
import re
import requests
import fitz  # pymupdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "data", "temp")


def _ensure_temp():
    os.makedirs(TEMP_DIR, exist_ok=True)


def extract_drive_file_id(url: str) -> str | None:
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def download_and_extract(url: str, filename: str, drive_client=None) -> dict:
    _ensure_temp()
    file_path = os.path.join(TEMP_DIR, filename)

    drive_id = extract_drive_file_id(url)
    if drive_id and drive_client:
        data = drive_client.download_file(drive_id)
        with open(file_path, "wb") as f:
            f.write(data)
    else:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(resp.content)

    return extract_from_file(file_path)


def extract_from_file(path: str) -> dict:
    doc = fitz.open(path)
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    full_text = "\n".join(pages_text)
    return {
        "filename": os.path.basename(path),
        "text": full_text,
        "page_count": len(pages_text),
        "file_path": path,
    }


def cleanup_temp():
    _ensure_temp()
    for fname in os.listdir(TEMP_DIR):
        fpath = os.path.join(TEMP_DIR, fname)
        try:
            os.remove(fpath)
        except Exception:
            pass
