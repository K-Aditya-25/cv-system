from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path


def document_body(chat_id: int, path: Path) -> tuple[bytes, str]:
    boundary = f"----cvbot{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    lines = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
        f"filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n",
    ]
    body = lines[0].encode() + lines[1].encode() + path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"
