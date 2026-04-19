import json
import logging
import os
from datetime import datetime, timezone


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("instaflow")


def load_captions(path: str) -> dict[str, str]:
    """Parse captions.txt → {filename: 'caption text\n\n#hashtags'}"""
    captions = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(" | ", 2)]
            if len(parts) != 3:
                logging.getLogger("instaflow").warning(
                    "Skipping malformed caption line (expected 3 columns): %r", line
                )
                continue
            filename, caption_text, hashtags = parts
            captions[filename] = f"{caption_text}\n\n{hashtags}"
    return captions


def load_posted(path: str) -> list[dict]:
    """Read posted.json; return [] if missing."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"posted.json must contain a JSON array, got {type(data).__name__}")
    return data


def mark_posted(path: str, filename: str, post_id: str) -> None:
    """Append a new entry to posted.json (atomic write)."""
    existing = load_posted(path)
    existing.append({
        "file": filename,
        "post_id": post_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    os.replace(tmp_path, path)


def get_next_image(
    images_dir: str,
    captions: dict[str, str],
    posted: list[dict],
) -> tuple[str, str] | None:
    """Return (filepath, full_caption) for the next unposted file, or None."""
    posted_files = {entry["file"] for entry in posted}
    all_files = sorted(
        f for f in os.listdir(images_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".mp4"))
    )
    for filename in all_files:
        if filename in posted_files:
            continue
        if filename not in captions:
            logging.getLogger("instaflow").warning(
                "No caption found for %s — skipping", filename
            )
            continue
        return os.path.join(images_dir, filename), captions[filename]
    return None


def detect_media_type(filepath: str) -> str:
    """Return 'IMAGE' or 'REELS' based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".mp4":
        return "REELS"
    return "IMAGE"
