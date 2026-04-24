import os
import re
import base64
import email
from email.message import Message
from bs4 import BeautifulSoup


def extract_images(msg: Message, save_dir: str):
    os.makedirs(save_dir, exist_ok=True)

    saved_files = []

    # -------------------------
    # 1. Extract attachments (FedEx sometimes uses these)
    # -------------------------
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))

        if "image" in content_type or "attachment" in content_disposition:
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                ext = content_type.split("/")[-1]
                filename = f"img_{len(saved_files)}.{ext}"

                path = os.path.join(save_dir, filename)
                with open(path, "wb") as f:
                    f.write(payload)

                saved_files.append(path)
            except Exception:
                continue

    # -------------------------
    # 2. Extract HTML images (img src)
    # -------------------------
    html = None
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            html = part.get_payload(decode=True)
            if html:
                html = html.decode(errors="ignore")
                break

    if not html:
        return saved_files

    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue

        # -------------------------
        # CID images (embedded)
        # -------------------------
        if src.startswith("cid:"):
            cid = src.replace("cid:", "").strip()

            for part in msg.walk():
                if part.get("Content-ID"):
                    content_id = part.get("Content-ID").strip("<>")
                    if content_id == cid:
                        payload = part.get_payload(decode=True)
                        if payload:
                            filename = f"cid_{len(saved_files)}.jpg"
                            path = os.path.join(save_dir, filename)

                            with open(path, "wb") as f:
                                f.write(payload)

                            saved_files.append(path)

        # -------------------------
        # Base64 inline images
        # -------------------------
        elif src.startswith("data:image"):
            try:
                header, encoded = src.split(",", 1)
                data = base64.b64decode(encoded)

                filename = f"inline_{len(saved_files)}.jpg"
                path = os.path.join(save_dir, filename)

                with open(path, "wb") as f:
                    f.write(data)

                saved_files.append(path)
            except Exception:
                continue

        # -------------------------
        # Remote images (FedEx sometimes uses these)
        # -------------------------
        elif src.startswith("http"):
            # NOTE: we are not downloading remote images yet
            # (can add later if needed)
            pass

    return saved_files