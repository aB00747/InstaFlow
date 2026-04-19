import json
import os
import tempfile
import pytest
from scripts.utils import (
    load_captions,
    load_posted,
    mark_posted,
    get_next_image,
    detect_media_type,
)


# --- load_captions ---

def test_load_captions_parses_three_columns():
    content = "post001.jpg | Hello world | #tag1 #tag2\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        captions = load_captions(path)
        assert captions["post001.jpg"] == "Hello world\n\n#tag1 #tag2"
    finally:
        os.unlink(path)


def test_load_captions_ignores_comment_lines():
    content = "# this is a comment\npost001.jpg | Caption | #tag\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        captions = load_captions(path)
        assert "# this is a comment" not in captions
        assert "post001.jpg" in captions
    finally:
        os.unlink(path)


def test_load_captions_ignores_blank_lines():
    content = "\npost001.jpg | Caption | #tag\n\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        captions = load_captions(path)
        assert len(captions) == 1
    finally:
        os.unlink(path)


# --- load_posted ---

def test_load_posted_returns_empty_list_when_file_missing():
    posted = load_posted("/nonexistent/path/posted.json")
    assert posted == []


def test_load_posted_returns_list_from_file():
    data = [{"file": "post001.jpg", "post_id": "123", "timestamp": "2026-01-01T09:00:00"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    try:
        posted = load_posted(path)
        assert posted == data
    finally:
        os.unlink(path)


# --- mark_posted ---

def test_mark_posted_appends_entry():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([], f)
        path = f.name
    try:
        mark_posted(path, "post001.jpg", "abc123")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["file"] == "post001.jpg"
        assert data[0]["post_id"] == "abc123"
        assert "timestamp" in data[0]
    finally:
        os.unlink(path)


def test_mark_posted_preserves_existing_entries():
    existing = [{"file": "post000.jpg", "post_id": "old", "timestamp": "2026-01-01T00:00:00"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(existing, f)
        path = f.name
    try:
        mark_posted(path, "post001.jpg", "new_id")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["file"] == "post000.jpg"
        assert data[1]["file"] == "post001.jpg"
    finally:
        os.unlink(path)


# --- get_next_image ---

def test_get_next_image_returns_first_unposted(tmp_path):
    # Create image files
    (tmp_path / "post001.jpg").write_bytes(b"fake")
    (tmp_path / "post002.jpg").write_bytes(b"fake")
    captions = {
        "post001.jpg": "Caption 1\n\n#tag",
        "post002.jpg": "Caption 2\n\n#tag",
    }
    posted = [{"file": "post001.jpg", "post_id": "x", "timestamp": "t"}]
    result = get_next_image(str(tmp_path), captions, posted)
    assert result is not None
    filepath, caption = result
    assert os.path.basename(filepath) == "post002.jpg"
    assert caption == "Caption 2\n\n#tag"


def test_get_next_image_returns_none_when_all_posted(tmp_path):
    (tmp_path / "post001.jpg").write_bytes(b"fake")
    captions = {"post001.jpg": "Caption\n\n#tag"}
    posted = [{"file": "post001.jpg", "post_id": "x", "timestamp": "t"}]
    result = get_next_image(str(tmp_path), captions, posted)
    assert result is None


def test_get_next_image_skips_file_with_no_caption(tmp_path):
    (tmp_path / "post001.jpg").write_bytes(b"fake")
    (tmp_path / "post002.jpg").write_bytes(b"fake")
    captions = {"post002.jpg": "Caption 2\n\n#tag"}  # post001 has no caption
    posted = []
    result = get_next_image(str(tmp_path), captions, posted)
    assert result is not None
    filepath, _ = result
    assert os.path.basename(filepath) == "post002.jpg"


def test_get_next_image_alphabetical_order(tmp_path):
    (tmp_path / "post003.jpg").write_bytes(b"fake")
    (tmp_path / "post001.jpg").write_bytes(b"fake")
    (tmp_path / "post002.jpg").write_bytes(b"fake")
    captions = {
        "post001.jpg": "C1",
        "post002.jpg": "C2",
        "post003.jpg": "C3",
    }
    posted = []
    result = get_next_image(str(tmp_path), captions, posted)
    assert os.path.basename(result[0]) == "post001.jpg"


# --- detect_media_type ---

def test_detect_media_type_jpg_is_image():
    assert detect_media_type("post001.jpg") == "IMAGE"

def test_detect_media_type_jpeg_is_image():
    assert detect_media_type("post001.jpeg") == "IMAGE"

def test_detect_media_type_png_is_image():
    assert detect_media_type("post001.png") == "IMAGE"

def test_detect_media_type_mp4_is_reel():
    assert detect_media_type("post001.mp4") == "REELS"

def test_detect_media_type_case_insensitive():
    assert detect_media_type("post001.JPG") == "IMAGE"
    assert detect_media_type("post001.MP4") == "REELS"
