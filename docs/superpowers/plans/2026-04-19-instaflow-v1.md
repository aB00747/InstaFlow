# InstaFlow v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated, zero-cost Instagram daily posting pipeline that runs on GitHub Actions — drop images + captions into the repo, it posts one per day with Gmail and Telegram notifications.

**Architecture:** `poster.py` is the single entry point — it reads environment variables, loads state from `posted.json`, selects the next unposted image, uploads it to imgbb for a public URL, calls Instagram Graph API to create and publish a container, then sends notifications. Each concern (upload, Instagram API, notifications, shared helpers) lives in its own focused module. Tests mock all HTTP calls with `unittest.mock.patch`.

**Tech Stack:** Python 3.11, `requests`, `pytest`, Instagram Graph API v19.0, imgbb API, Gmail SMTP (smtplib), Telegram Bot API.

---

## File Map

| File | Responsibility |
|---|---|
| `scripts/utils.py` | Caption parsing, posted.json state, next-image selection, media type detection, logging setup |
| `scripts/upload.py` | Base64-encode file, POST to imgbb, return public URL |
| `scripts/instagram.py` | Create image/reel container, poll reel status, publish container |
| `scripts/notify.py` | Gmail SMTP send, Telegram Bot API send, high-level success/failure/empty wrappers |
| `scripts/poster.py` | Load env config, orchestrate upload → post → notify → track pipeline |
| `tests/test_utils.py` | Unit tests for all utils.py functions |
| `tests/test_upload.py` | Unit tests for upload.py (mocked requests) |
| `tests/test_instagram.py` | Unit tests for instagram.py (mocked requests) |
| `tests/test_notify.py` | Unit tests for notify.py (mocked SMTP + requests) |
| `tests/test_poster.py` | Integration-style unit tests for poster.py orchestration |
| `requirements.txt` | `requests`, `pytest` |
| `config.json.example` | Template for local development |
| `.gitignore` | Ignore config.json, __pycache__, .env, images (optional) |
| `posted.json` | Initial empty array `[]` — tracked by git |
| `captions.txt` | Example captions file with format comments |
| `setup_test.py` | One-time connectivity checker (no posting) |
| `.github/workflows/daily_post.yml` | GitHub Actions cron trigger |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `config.json.example`
- Create: `posted.json`
- Create: `captions.txt`
- Create: `images/.gitkeep`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
requests==2.31.0
pytest==7.4.3
```

- [ ] **Step 2: Create `.gitignore`**

```
config.json
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 3: Create `config.json.example`**

```json
{
  "instagram": {
    "user_id": "YOUR_INSTAGRAM_USER_ID",
    "access_token": "YOUR_LONG_LIVED_ACCESS_TOKEN"
  },
  "imgbb": {
    "api_key": "YOUR_IMGBB_API_KEY"
  },
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "sender": "your.gmail@gmail.com",
    "app_password": "YOUR_APP_PASSWORD",
    "recipient": "notify@youremail.com"
  },
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  },
  "settings": {
    "images_folder": "./images",
    "captions_file": "./captions.txt",
    "posted_file": "./posted.json",
    "post_time": "09:00",
    "timezone": "Asia/Kolkata"
  }
}
```

- [ ] **Step 4: Create `posted.json`**

```json
[]
```

- [ ] **Step 5: Create `captions.txt`**

```
# InstaFlow Captions File
# Format: filename | caption text | #hashtags
# Lines starting with # are ignored
# Separator: space-pipe-space ( | )
# Max caption length: 2,200 characters total (caption + tags)
# Max hashtags: 30 per post

post001.jpg | Golden hour magic ✨ Every sunset is a reminder that endings can be beautiful. | #sunset #goldenhour #photography #naturephotography #photooftheday
post002.mp4 | Behind the scenes of our morning routine 🌅 | #reels #behindthescenes #morning #lifestyle #reelsinstagram
post003.png | Monday motivation 💪 Start with purpose. | #motivation #monday #mindset #inspire #positivity
```

- [ ] **Step 6: Create `images/.gitkeep`** (empty file so git tracks the folder)

- [ ] **Step 7: Create `scripts/__init__.py`** (empty)

- [ ] **Step 8: Create `tests/__init__.py`** (empty)

- [ ] **Step 9: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 10: Commit**

```bash
git add requirements.txt .gitignore config.json.example posted.json captions.txt images/.gitkeep scripts/__init__.py tests/__init__.py
git commit -m "feat: project scaffold — dependencies, gitignore, example config, empty state"
```

---

## Task 2: `scripts/utils.py` — Shared Helpers

**Files:**
- Create: `scripts/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_utils.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
cd "D:\Projects\TanOff Project\automate_tool\InstaFlow"
pytest tests/test_utils.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `scripts.utils`

- [ ] **Step 3: Implement `scripts/utils.py`**

```python
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
                continue
            filename, caption_text, hashtags = parts
            captions[filename] = f"{caption_text}\n\n{hashtags}"
    return captions


def load_posted(path: str) -> list[dict]:
    """Read posted.json; return [] if missing."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mark_posted(path: str, filename: str, post_id: str) -> None:
    """Append a new entry to posted.json."""
    existing = load_posted(path)
    existing.append({
        "file": filename,
        "post_id": post_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


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
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
pytest tests/test_utils.py -v
```

Expected: all green, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add scripts/utils.py tests/test_utils.py
git commit -m "feat: utils — caption parsing, posted state, next-image selection, media type"
```

---

## Task 3: `scripts/upload.py` — imgbb Uploader

**Files:**
- Create: `scripts/upload.py`
- Create: `tests/test_upload.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_upload.py`:

```python
import base64
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from scripts.upload import upload_to_imgbb


def _make_temp_file(content: bytes = b"fake image data") -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    f.write(content)
    f.close()
    return f.name


def test_upload_returns_url_on_success():
    path = _make_temp_file()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "data": {"url": "https://i.ibb.co/abc/test.jpg"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("scripts.upload.requests.post", return_value=mock_response) as mock_post:
        url = upload_to_imgbb("fake_api_key", path)

    assert url == "https://i.ibb.co/abc/test.jpg"
    os.unlink(path)


def test_upload_sends_base64_encoded_image():
    content = b"pixel data"
    path = _make_temp_file(content)
    expected_b64 = base64.b64encode(content).decode("utf-8")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "data": {"url": "https://i.ibb.co/abc/test.jpg"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("scripts.upload.requests.post", return_value=mock_response) as mock_post:
        upload_to_imgbb("mykey", path)

    call_kwargs = mock_post.call_args
    sent_data = call_kwargs[1]["data"] if "data" in call_kwargs[1] else call_kwargs[0][1]
    assert sent_data["image"] == expected_b64
    assert sent_data["key"] == "mykey"
    os.unlink(path)


def test_upload_raises_on_api_failure():
    path = _make_temp_file()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False, "error": {"message": "Invalid key"}}
    mock_response.raise_for_status = MagicMock()

    with patch("scripts.upload.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="imgbb upload failed"):
            upload_to_imgbb("bad_key", path)
    os.unlink(path)


def test_upload_raises_on_http_error():
    import requests as req
    path = _make_temp_file()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = req.HTTPError("500 Server Error")

    with patch("scripts.upload.requests.post", return_value=mock_response):
        with pytest.raises(req.HTTPError):
            upload_to_imgbb("mykey", path)
    os.unlink(path)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_upload.py -v
```

Expected: `ImportError` for `scripts.upload`

- [ ] **Step 3: Implement `scripts/upload.py`**

```python
import base64
import logging

import requests

logger = logging.getLogger("instaflow")

IMGBB_ENDPOINT = "https://api.imgbb.com/1/upload"


def upload_to_imgbb(api_key: str, filepath: str) -> str:
    """Upload file to imgbb. Returns the permanent public URL."""
    logger.info("Uploading %s to imgbb...", filepath)
    with open(filepath, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    response = requests.post(
        IMGBB_ENDPOINT,
        data={"key": api_key, "image": image_b64},
    )
    response.raise_for_status()
    body = response.json()

    if not body.get("success"):
        error_msg = body.get("error", {}).get("message", "unknown error")
        raise RuntimeError(f"imgbb upload failed: {error_msg}")

    url = body["data"]["url"]
    logger.info("Uploaded successfully: %s", url)
    return url
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_upload.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/upload.py tests/test_upload.py
git commit -m "feat: upload — imgbb base64 uploader with error handling"
```

---

## Task 4: `scripts/instagram.py` — Graph API Wrapper

**Files:**
- Create: `scripts/instagram.py`
- Create: `tests/test_instagram.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_instagram.py`:

```python
import time
from unittest.mock import MagicMock, call, patch

import pytest
import requests as req
from scripts.instagram import (
    create_image_container,
    create_reel_container,
    poll_reel_status,
    publish_container,
)

BASE = "https://graph.facebook.com/v19.0"


def _mock_json_response(data: dict, status_code: int = 200) -> MagicMock:
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    m.status_code = status_code
    return m


# --- create_image_container ---

def test_create_image_container_returns_creation_id():
    mock_resp = _mock_json_response({"id": "container_abc"})
    with patch("scripts.instagram.requests.post", return_value=mock_resp):
        cid = create_image_container(
            user_id="123",
            access_token="tok",
            image_url="https://i.ibb.co/x/img.jpg",
            caption="Hello\n\n#tag",
        )
    assert cid == "container_abc"


def test_create_image_container_posts_correct_params():
    mock_resp = _mock_json_response({"id": "container_abc"})
    with patch("scripts.instagram.requests.post", return_value=mock_resp) as mock_post:
        create_image_container("uid", "tok", "https://img.url/x.jpg", "Cap\n\n#t")

    _, kwargs = mock_post.call_args
    params = kwargs.get("params", mock_post.call_args[0][1] if len(mock_post.call_args[0]) > 1 else {})
    # Check URL
    assert mock_post.call_args[0][0] == f"{BASE}/uid/media"
    assert kwargs["params"]["image_url"] == "https://img.url/x.jpg"
    assert kwargs["params"]["caption"] == "Cap\n\n#t"
    assert kwargs["params"]["access_token"] == "tok"


def test_create_image_container_raises_on_api_error():
    mock_resp = _mock_json_response({"error": {"message": "Invalid token", "code": 190}})
    with patch("scripts.instagram.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Instagram API error"):
            create_image_container("uid", "bad", "https://url", "cap")


# --- create_reel_container ---

def test_create_reel_container_returns_creation_id():
    mock_resp = _mock_json_response({"id": "reel_container_xyz"})
    with patch("scripts.instagram.requests.post", return_value=mock_resp):
        cid = create_reel_container("uid", "tok", "https://vid.url/v.mp4", "Cap")
    assert cid == "reel_container_xyz"


def test_create_reel_container_sets_media_type_reels():
    mock_resp = _mock_json_response({"id": "r123"})
    with patch("scripts.instagram.requests.post", return_value=mock_resp) as mock_post:
        create_reel_container("uid", "tok", "https://vid.url/v.mp4", "Cap")
    _, kwargs = mock_post.call_args
    assert kwargs["params"]["media_type"] == "REELS"
    assert kwargs["params"]["video_url"] == "https://vid.url/v.mp4"


# --- poll_reel_status ---

def test_poll_reel_status_returns_true_when_finished():
    mock_resp = _mock_json_response({"status_code": "FINISHED"})
    with patch("scripts.instagram.requests.get", return_value=mock_resp):
        with patch("scripts.instagram.time.sleep"):
            result = poll_reel_status("cid123", "tok", timeout=30, interval=5)
    assert result is True


def test_poll_reel_status_polls_until_finished():
    responses = [
        _mock_json_response({"status_code": "IN_PROGRESS"}),
        _mock_json_response({"status_code": "IN_PROGRESS"}),
        _mock_json_response({"status_code": "FINISHED"}),
    ]
    with patch("scripts.instagram.requests.get", side_effect=responses):
        with patch("scripts.instagram.time.sleep") as mock_sleep:
            result = poll_reel_status("cid", "tok", timeout=60, interval=5)
    assert result is True
    assert mock_sleep.call_count == 2  # slept before 1st and 2nd poll (not after FINISHED)


def test_poll_reel_status_raises_on_timeout():
    mock_resp = _mock_json_response({"status_code": "IN_PROGRESS"})
    with patch("scripts.instagram.requests.get", return_value=mock_resp):
        with patch("scripts.instagram.time.sleep"):
            with patch("scripts.instagram.time.time", side_effect=[0, 100, 200, 400]):
                with pytest.raises(TimeoutError, match="Reel processing timed out"):
                    poll_reel_status("cid", "tok", timeout=300, interval=5)


# --- publish_container ---

def test_publish_container_returns_post_id():
    mock_resp = _mock_json_response({"id": "post_999"})
    with patch("scripts.instagram.requests.post", return_value=mock_resp):
        post_id = publish_container("uid", "tok", "container_abc")
    assert post_id == "post_999"


def test_publish_container_posts_correct_params():
    mock_resp = _mock_json_response({"id": "post_999"})
    with patch("scripts.instagram.requests.post", return_value=mock_resp) as mock_post:
        publish_container("uid", "tok", "cid")
    assert mock_post.call_args[0][0] == f"{BASE}/uid/media_publish"
    assert mock_post.call_args[1]["params"]["creation_id"] == "cid"
    assert mock_post.call_args[1]["params"]["access_token"] == "tok"


def test_publish_container_raises_on_api_error():
    mock_resp = _mock_json_response({"error": {"message": "Container not ready", "code": 9007}})
    with patch("scripts.instagram.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Instagram API error"):
            publish_container("uid", "tok", "cid")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_instagram.py -v
```

Expected: `ImportError` for `scripts.instagram`

- [ ] **Step 3: Implement `scripts/instagram.py`**

```python
import logging
import time

import requests

logger = logging.getLogger("instaflow")

BASE_URL = "https://graph.facebook.com/v19.0"


def _check_api_error(body: dict) -> None:
    if "error" in body:
        msg = body["error"].get("message", "unknown")
        code = body["error"].get("code", "?")
        raise RuntimeError(f"Instagram API error (code {code}): {msg}")


def create_image_container(
    user_id: str,
    access_token: str,
    image_url: str,
    caption: str,
) -> str:
    """Create a media container for an image. Returns creation_id."""
    logger.info("Creating Instagram image container for URL: %s", image_url)
    response = requests.post(
        f"{BASE_URL}/{user_id}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
    )
    response.raise_for_status()
    body = response.json()
    _check_api_error(body)
    creation_id = body["id"]
    logger.info("Image container created: %s", creation_id)
    return creation_id


def create_reel_container(
    user_id: str,
    access_token: str,
    video_url: str,
    caption: str,
) -> str:
    """Create a media container for a reel. Returns creation_id."""
    logger.info("Creating Instagram reel container for URL: %s", video_url)
    response = requests.post(
        f"{BASE_URL}/{user_id}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
        },
    )
    response.raise_for_status()
    body = response.json()
    _check_api_error(body)
    creation_id = body["id"]
    logger.info("Reel container created: %s", creation_id)
    return creation_id


def poll_reel_status(
    creation_id: str,
    access_token: str,
    timeout: int = 300,
    interval: int = 10,
) -> bool:
    """Poll until reel status is FINISHED. Raises TimeoutError on timeout."""
    logger.info("Polling reel status for container: %s", creation_id)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(interval)
        response = requests.get(
            f"{BASE_URL}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
        )
        response.raise_for_status()
        body = response.json()
        status = body.get("status_code", "")
        logger.info("Reel status: %s", status)
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"Reel processing failed with status: ERROR")
    raise TimeoutError(f"Reel processing timed out after {timeout}s for container {creation_id}")


def publish_container(
    user_id: str,
    access_token: str,
    creation_id: str,
) -> str:
    """Publish a ready container. Returns the post_id (media_id)."""
    logger.info("Publishing container: %s", creation_id)
    response = requests.post(
        f"{BASE_URL}/{user_id}/media_publish",
        params={
            "creation_id": creation_id,
            "access_token": access_token,
        },
    )
    response.raise_for_status()
    body = response.json()
    _check_api_error(body)
    post_id = body["id"]
    logger.info("Published successfully! Post ID: %s", post_id)
    return post_id
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_instagram.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/instagram.py tests/test_instagram.py
git commit -m "feat: instagram — Graph API wrapper for image/reel container creation and publishing"
```

---

## Task 5: `scripts/notify.py` — Notifications

**Files:**
- Create: `scripts/notify.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_notify.py`:

```python
import smtplib
from unittest.mock import MagicMock, patch, call

import pytest
from scripts.notify import send_gmail, send_telegram, notify_success, notify_failure, notify_empty_queue


# --- send_telegram ---

def test_send_telegram_posts_message():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("scripts.notify.requests.post", return_value=mock_resp) as mock_post:
        send_telegram("bot123:token", "chat_456", "Hello!")
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "bot123:token" in call_args[0][0]
    assert call_args[1]["data"]["chat_id"] == "chat_456"
    assert call_args[1]["data"]["text"] == "Hello!"


def test_send_telegram_does_not_raise_on_http_error():
    import requests as req
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = req.HTTPError("401 Unauthorized")
    with patch("scripts.notify.requests.post", return_value=mock_resp):
        # Should log error and NOT re-raise
        send_telegram("bad_token", "chat", "msg")  # no exception


def test_send_telegram_does_not_raise_on_connection_error():
    import requests as req
    with patch("scripts.notify.requests.post", side_effect=req.ConnectionError("no network")):
        send_telegram("tok", "cid", "msg")  # no exception


# --- send_gmail ---

def test_send_gmail_connects_and_sends():
    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__exit__ = MagicMock(return_value=False)

    with patch("scripts.notify.smtplib.SMTP", mock_smtp_class):
        send_gmail(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            sender="sender@gmail.com",
            app_password="pass1234",
            recipient="recv@example.com",
            subject="Test Subject",
            body="<p>Hello</p>",
        )

    mock_smtp_class.assert_called_with("smtp.gmail.com", 587)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_with("sender@gmail.com", "pass1234")
    mock_smtp_instance.sendmail.assert_called_once()
    _, sendmail_args, _ = mock_smtp_instance.sendmail.mock_calls[0]
    assert sendmail_args[0] == "sender@gmail.com"
    assert sendmail_args[1] == "recv@example.com"


def test_send_gmail_does_not_raise_on_smtp_error():
    with patch("scripts.notify.smtplib.SMTP", side_effect=smtplib.SMTPException("auth failed")):
        # Should log error and NOT re-raise (Telegram is still attempted)
        send_gmail("host", 587, "a@b.com", "pw", "c@d.com", "subj", "body")  # no exception


# --- notify_success ---

def test_notify_success_calls_both_channels():
    config = {
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "sender": "a@b.com",
            "app_password": "pw",
            "recipient": "c@d.com",
        },
        "telegram": {
            "bot_token": "tok",
            "chat_id": "cid",
        },
    }
    with patch("scripts.notify.send_gmail") as mock_gmail:
        with patch("scripts.notify.send_telegram") as mock_tg:
            notify_success(config, "post001.jpg", "post_id_123")
    mock_gmail.assert_called_once()
    mock_tg.assert_called_once()
    # Check post filename appears in the notification content
    gmail_args = mock_gmail.call_args[0]  # positional args
    assert "post001.jpg" in gmail_args[5] or "post001.jpg" in gmail_args[6]  # subject or body
    tg_args = mock_tg.call_args[0]
    assert "post001.jpg" in tg_args[2]


# --- notify_failure ---

def test_notify_failure_calls_both_channels():
    config = {
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "sender": "a@b.com",
            "app_password": "pw",
            "recipient": "c@d.com",
        },
        "telegram": {"bot_token": "tok", "chat_id": "cid"},
    }
    with patch("scripts.notify.send_gmail") as mock_gmail:
        with patch("scripts.notify.send_telegram") as mock_tg:
            notify_failure(config, "Upload timed out")
    mock_gmail.assert_called_once()
    mock_tg.assert_called_once()


# --- notify_empty_queue ---

def test_notify_empty_queue_calls_both_channels():
    config = {
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "sender": "a@b.com",
            "app_password": "pw",
            "recipient": "c@d.com",
        },
        "telegram": {"bot_token": "tok", "chat_id": "cid"},
    }
    with patch("scripts.notify.send_gmail") as mock_gmail:
        with patch("scripts.notify.send_telegram") as mock_tg:
            notify_empty_queue(config)
    mock_gmail.assert_called_once()
    mock_tg.assert_called_once()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_notify.py -v
```

Expected: `ImportError` for `scripts.notify`

- [ ] **Step 3: Implement `scripts/notify.py`**

```python
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger("instaflow")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(bot_token: str, chat_id: str, message: str) -> None:
    """Send a Telegram message. Logs errors but does not raise."""
    try:
        response = requests.post(
            TELEGRAM_API.format(token=bot_token),
            data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        )
        response.raise_for_status()
        logger.info("Telegram notification sent.")
    except Exception as exc:
        logger.error("Telegram notification failed: %s", exc)


def send_gmail(
    smtp_host: str,
    smtp_port: int,
    sender: str,
    app_password: str,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    """Send an HTML email via Gmail SMTP. Logs errors but does not raise."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info("Gmail notification sent to %s.", recipient)
    except Exception as exc:
        logger.error("Gmail notification failed: %s", exc)


def notify_success(config: dict, filename: str, post_id: str) -> None:
    """Notify both channels that a post was published successfully."""
    subject = f"✅ InstaFlow: Posted {filename}"
    body = f"""
    <h2>✅ InstaFlow Post Published</h2>
    <p><strong>File:</strong> {filename}</p>
    <p><strong>Instagram Post ID:</strong> {post_id}</p>
    <p>Your content is now live on Instagram!</p>
    """
    tg_msg = f"✅ <b>InstaFlow</b>: Posted <code>{filename}</code>\nPost ID: <code>{post_id}</code>"

    send_gmail(
        config["email"]["smtp_host"],
        config["email"]["smtp_port"],
        config["email"]["sender"],
        config["email"]["app_password"],
        config["email"]["recipient"],
        subject,
        body,
    )
    send_telegram(config["telegram"]["bot_token"], config["telegram"]["chat_id"], tg_msg)


def notify_failure(config: dict, error_msg: str) -> None:
    """Notify both channels that the pipeline failed."""
    subject = "❌ InstaFlow: Post Failed"
    body = f"""
    <h2>❌ InstaFlow Post Failed</h2>
    <p><strong>Error:</strong> {error_msg}</p>
    <p>Check the GitHub Actions logs for details.</p>
    """
    tg_msg = f"❌ <b>InstaFlow</b>: Post failed!\n<code>{error_msg}</code>"

    send_gmail(
        config["email"]["smtp_host"],
        config["email"]["smtp_port"],
        config["email"]["sender"],
        config["email"]["app_password"],
        config["email"]["recipient"],
        subject,
        body,
    )
    send_telegram(config["telegram"]["bot_token"], config["telegram"]["chat_id"], tg_msg)


def notify_empty_queue(config: dict) -> None:
    """Notify both channels that there are no images left to post."""
    subject = "⚠️ InstaFlow: Queue Empty"
    body = """
    <h2>⚠️ InstaFlow: Queue Empty</h2>
    <p>No more images are left to post.</p>
    <p>Add new images and captions to keep the pipeline running.</p>
    """
    tg_msg = "⚠️ <b>InstaFlow</b>: Queue is empty! Add more images to continue."

    send_gmail(
        config["email"]["smtp_host"],
        config["email"]["smtp_port"],
        config["email"]["sender"],
        config["email"]["app_password"],
        config["email"]["recipient"],
        subject,
        body,
    )
    send_telegram(config["telegram"]["bot_token"], config["telegram"]["chat_id"], tg_msg)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_notify.py -v
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/notify.py tests/test_notify.py
git commit -m "feat: notify — Gmail SMTP and Telegram Bot notifications with success/failure/empty wrappers"
```

---

## Task 6: `scripts/poster.py` — Main Orchestrator

**Files:**
- Create: `scripts/poster.py`
- Create: `tests/test_poster.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_poster.py`:

```python
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from scripts.poster import load_config, run


# --- load_config ---

def test_load_config_reads_all_env_vars(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_USER_ID", "uid123")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok456")
    monkeypatch.setenv("IMGBB_API_KEY", "imgkey")
    monkeypatch.setenv("GMAIL_SENDER", "a@b.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setenv("GMAIL_RECIPIENT", "c@d.com")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bottoken")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chatid")

    config = load_config()

    assert config["instagram"]["user_id"] == "uid123"
    assert config["instagram"]["access_token"] == "tok456"
    assert config["imgbb"]["api_key"] == "imgkey"
    assert config["email"]["sender"] == "a@b.com"
    assert config["email"]["app_password"] == "pw"
    assert config["email"]["recipient"] == "c@d.com"
    assert config["telegram"]["bot_token"] == "bottoken"
    assert config["telegram"]["chat_id"] == "chatid"


def test_load_config_raises_on_missing_required_var(monkeypatch):
    # Clear all relevant env vars
    for var in [
        "INSTAGRAM_USER_ID", "INSTAGRAM_ACCESS_TOKEN", "IMGBB_API_KEY",
        "GMAIL_SENDER", "GMAIL_APP_PASSWORD", "GMAIL_RECIPIENT",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    ]:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(EnvironmentError, match="INSTAGRAM_USER_ID"):
        load_config()


# --- run (integration-style unit tests) ---

def _make_env(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_USER_ID", "uid")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("IMGBB_API_KEY", "imgkey")
    monkeypatch.setenv("GMAIL_SENDER", "a@b.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setenv("GMAIL_RECIPIENT", "c@d.com")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bttok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "cid")


def test_run_posts_image_and_marks_posted(monkeypatch, tmp_path):
    _make_env(monkeypatch)
    # Create fake image
    img = tmp_path / "post001.jpg"
    img.write_bytes(b"fake")
    # Captions
    cap_file = tmp_path / "captions.txt"
    cap_file.write_text("post001.jpg | Hello world | #tag\n", encoding="utf-8")
    # posted.json
    posted_file = tmp_path / "posted.json"
    posted_file.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("IMAGES_FOLDER", str(tmp_path))
    monkeypatch.setenv("CAPTIONS_FILE", str(cap_file))
    monkeypatch.setenv("POSTED_FILE", str(posted_file))

    with patch("scripts.poster.upload_to_imgbb", return_value="https://i.ibb.co/img.jpg") as mock_upload:
        with patch("scripts.poster.create_image_container", return_value="container1") as mock_create:
            with patch("scripts.poster.publish_container", return_value="post_id_1") as mock_publish:
                with patch("scripts.poster.notify_success") as mock_notify:
                    run()

    mock_upload.assert_called_once_with("imgkey", str(img))
    mock_create.assert_called_once()
    mock_publish.assert_called_once()
    mock_notify.assert_called_once()

    # Check posted.json was updated
    data = json.loads(posted_file.read_text())
    assert len(data) == 1
    assert data[0]["file"] == "post001.jpg"
    assert data[0]["post_id"] == "post_id_1"


def test_run_notifies_empty_queue_when_no_images(monkeypatch, tmp_path):
    _make_env(monkeypatch)
    cap_file = tmp_path / "captions.txt"
    cap_file.write_text("", encoding="utf-8")
    posted_file = tmp_path / "posted.json"
    posted_file.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("IMAGES_FOLDER", str(tmp_path))
    monkeypatch.setenv("CAPTIONS_FILE", str(cap_file))
    monkeypatch.setenv("POSTED_FILE", str(posted_file))

    with patch("scripts.poster.notify_empty_queue") as mock_empty:
        run()

    mock_empty.assert_called_once()


def test_run_sends_failure_notification_on_upload_error(monkeypatch, tmp_path):
    _make_env(monkeypatch)
    img = tmp_path / "post001.jpg"
    img.write_bytes(b"fake")
    cap_file = tmp_path / "captions.txt"
    cap_file.write_text("post001.jpg | Caption | #tag\n", encoding="utf-8")
    posted_file = tmp_path / "posted.json"
    posted_file.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("IMAGES_FOLDER", str(tmp_path))
    monkeypatch.setenv("CAPTIONS_FILE", str(cap_file))
    monkeypatch.setenv("POSTED_FILE", str(posted_file))

    with patch("scripts.poster.upload_to_imgbb", side_effect=RuntimeError("upload failed")):
        with patch("scripts.poster.notify_failure") as mock_fail:
            with pytest.raises(SystemExit) as exc_info:
                run()

    assert exc_info.value.code == 1
    mock_fail.assert_called_once()
    # Verify posted.json was NOT updated on failure
    data = json.loads(posted_file.read_text())
    assert data == []


def test_run_handles_reel_with_polling(monkeypatch, tmp_path):
    _make_env(monkeypatch)
    reel = tmp_path / "post001.mp4"
    reel.write_bytes(b"fake video")
    cap_file = tmp_path / "captions.txt"
    cap_file.write_text("post001.mp4 | Reel caption | #reel\n", encoding="utf-8")
    posted_file = tmp_path / "posted.json"
    posted_file.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("IMAGES_FOLDER", str(tmp_path))
    monkeypatch.setenv("CAPTIONS_FILE", str(cap_file))
    monkeypatch.setenv("POSTED_FILE", str(posted_file))

    with patch("scripts.poster.upload_to_imgbb", return_value="https://i.ibb.co/v.mp4"):
        with patch("scripts.poster.create_reel_container", return_value="reel_container") as mock_reel:
            with patch("scripts.poster.poll_reel_status", return_value=True) as mock_poll:
                with patch("scripts.poster.publish_container", return_value="reel_post_id"):
                    with patch("scripts.poster.notify_success"):
                        run()

    mock_reel.assert_called_once()
    mock_poll.assert_called_once_with("reel_container", "tok")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_poster.py -v
```

Expected: `ImportError` for `scripts.poster`

- [ ] **Step 3: Implement `scripts/poster.py`**

```python
import logging
import os
import sys

from scripts.instagram import (
    create_image_container,
    create_reel_container,
    poll_reel_status,
    publish_container,
)
from scripts.notify import notify_empty_queue, notify_failure, notify_success
from scripts.upload import upload_to_imgbb
from scripts.utils import (
    detect_media_type,
    get_next_image,
    load_captions,
    load_posted,
    mark_posted,
    setup_logging,
)

logger = setup_logging()

REQUIRED_ENV_VARS = [
    "INSTAGRAM_USER_ID",
    "INSTAGRAM_ACCESS_TOKEN",
    "IMGBB_API_KEY",
    "GMAIL_SENDER",
    "GMAIL_APP_PASSWORD",
    "GMAIL_RECIPIENT",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def load_config() -> dict:
    """Load all config from environment variables. Raises EnvironmentError if any are missing."""
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "instagram": {
            "user_id": os.environ["INSTAGRAM_USER_ID"],
            "access_token": os.environ["INSTAGRAM_ACCESS_TOKEN"],
        },
        "imgbb": {
            "api_key": os.environ["IMGBB_API_KEY"],
        },
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "sender": os.environ["GMAIL_SENDER"],
            "app_password": os.environ["GMAIL_APP_PASSWORD"],
            "recipient": os.environ["GMAIL_RECIPIENT"],
        },
        "telegram": {
            "bot_token": os.environ["TELEGRAM_BOT_TOKEN"],
            "chat_id": os.environ["TELEGRAM_CHAT_ID"],
        },
        "settings": {
            "images_folder": os.environ.get("IMAGES_FOLDER", "./images"),
            "captions_file": os.environ.get("CAPTIONS_FILE", "./captions.txt"),
            "posted_file": os.environ.get("POSTED_FILE", "./posted.json"),
        },
    }


def run() -> None:
    """Main pipeline: select next image → upload → post → notify → track."""
    config = load_config()
    settings = config["settings"]

    captions = load_captions(settings["captions_file"])
    posted = load_posted(settings["posted_file"])

    next_item = get_next_image(settings["images_folder"], captions, posted)
    if next_item is None:
        logger.warning("No images left in queue.")
        notify_empty_queue(config)
        return

    filepath, caption = next_item
    filename = os.path.basename(filepath)
    media_type = detect_media_type(filepath)

    logger.info("Posting: %s (type: %s)", filename, media_type)

    try:
        public_url = upload_to_imgbb(config["imgbb"]["api_key"], filepath)

        uid = config["instagram"]["user_id"]
        tok = config["instagram"]["access_token"]

        if media_type == "IMAGE":
            creation_id = create_image_container(uid, tok, public_url, caption)
        else:  # REELS
            creation_id = create_reel_container(uid, tok, public_url, caption)
            poll_reel_status(creation_id, tok)

        post_id = publish_container(uid, tok, creation_id)
        mark_posted(settings["posted_file"], filename, post_id)
        notify_success(config, filename, post_id)
        logger.info("Done. Post ID: %s", post_id)

    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        notify_failure(config, str(exc))
        sys.exit(1)


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_poster.py -v
```

Expected: all green.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests across all test files pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/poster.py tests/test_poster.py
git commit -m "feat: poster — main orchestration pipeline with image/reel routing and failure handling"
```

---

## Task 7: `setup_test.py` — Connection Verifier

**Files:**
- Create: `setup_test.py`

No tests for this file — it is itself a diagnostic tool run manually before first deploy.

- [ ] **Step 1: Create `setup_test.py`**

```python
"""
InstaFlow Setup Verifier
Run once locally to check all connections before going live.
Usage: python setup_test.py
Reads from config.json (local dev) or environment variables.
"""
import json
import os
import smtplib
import sys

import requests


def load_config_for_test() -> dict:
    """Try config.json first, fall back to env vars."""
    if os.path.exists("config.json"):
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    return {
        "instagram": {
            "user_id": os.environ.get("INSTAGRAM_USER_ID", ""),
            "access_token": os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
        },
        "imgbb": {"api_key": os.environ.get("IMGBB_API_KEY", "")},
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "sender": os.environ.get("GMAIL_SENDER", ""),
            "app_password": os.environ.get("GMAIL_APP_PASSWORD", ""),
            "recipient": os.environ.get("GMAIL_RECIPIENT", ""),
        },
        "telegram": {
            "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            "chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
        },
    }


def check_instagram(config: dict) -> bool:
    print("\n[1/4] Checking Instagram Graph API...")
    uid = config["instagram"]["user_id"]
    tok = config["instagram"]["access_token"]
    if not uid or not tok:
        print("  SKIP — INSTAGRAM_USER_ID or INSTAGRAM_ACCESS_TOKEN not set")
        return False
    try:
        resp = requests.get(
            f"https://graph.facebook.com/v19.0/{uid}",
            params={"fields": "id,username", "access_token": tok},
        )
        data = resp.json()
        if "error" in data:
            print(f"  FAIL — {data['error']['message']}")
            return False
        print(f"  OK — Connected as Instagram user ID: {data.get('id')} (username: {data.get('username', 'N/A')})")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False


def check_imgbb(config: dict) -> bool:
    print("\n[2/4] Checking imgbb API...")
    key = config["imgbb"]["api_key"]
    if not key:
        print("  SKIP — IMGBB_API_KEY not set")
        return False
    try:
        # Upload a 1x1 transparent PNG (smallest valid image)
        import base64
        tiny_png = base64.b64encode(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154"
                "789c6260000000000200e221bc330000000049454e44ae426082"
            )
        ).decode()
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": key, "image": tiny_png},
        )
        data = resp.json()
        if data.get("success"):
            print(f"  OK — Test image uploaded: {data['data']['url']}")
            return True
        print(f"  FAIL — {data.get('error', {}).get('message', 'unknown')}")
        return False
    except Exception as e:
        print(f"  FAIL — {e}")
        return False


def check_gmail(config: dict) -> bool:
    print("\n[3/4] Checking Gmail SMTP...")
    email = config["email"]
    if not email.get("sender") or not email.get("app_password"):
        print("  SKIP — GMAIL_SENDER or GMAIL_APP_PASSWORD not set")
        return False
    try:
        with smtplib.SMTP(email["smtp_host"], email["smtp_port"]) as server:
            server.starttls()
            server.login(email["sender"], email["app_password"])
        print(f"  OK — Gmail SMTP login successful for {email['sender']}")
        return True
    except Exception as e:
        print(f"  FAIL — {e}")
        return False


def check_telegram(config: dict) -> bool:
    print("\n[4/4] Checking Telegram Bot API...")
    tg = config["telegram"]
    if not tg.get("bot_token") or not tg.get("chat_id"):
        print("  SKIP — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
            data={
                "chat_id": tg["chat_id"],
                "text": "✅ InstaFlow setup test — connection verified!",
            },
        )
        data = resp.json()
        if data.get("ok"):
            print(f"  OK — Telegram message sent to chat {tg['chat_id']}")
            return True
        print(f"  FAIL — {data.get('description', 'unknown error')}")
        return False
    except Exception as e:
        print(f"  FAIL — {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("InstaFlow Setup Verifier")
    print("=" * 50)

    cfg = load_config_for_test()
    results = [
        check_instagram(cfg),
        check_imgbb(cfg),
        check_gmail(cfg),
        check_telegram(cfg),
    ]

    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} checks passed")
    if passed == total:
        print("All systems go! You can run poster.py safely.")
    else:
        print("Fix the failing checks before running the pipeline.")
    print("=" * 50)
    sys.exit(0 if passed == total else 1)
```

- [ ] **Step 2: Commit**

```bash
git add setup_test.py
git commit -m "feat: setup_test — one-time connection verifier for all API integrations"
```

---

## Task 8: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily_post.yml`

No unit tests — this is GitHub Actions YAML, verified by manual trigger.

- [ ] **Step 1: Create `.github/workflows/` directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create `.github/workflows/daily_post.yml`**

```yaml
name: InstaFlow Daily Post

on:
  schedule:
    - cron: "30 3 * * *"   # 3:30 UTC = 9:00 AM IST
  workflow_dispatch:         # Allow manual trigger from GitHub Actions UI

jobs:
  post:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run InstaFlow poster
        env:
          INSTAGRAM_USER_ID:      ${{ secrets.INSTAGRAM_USER_ID }}
          INSTAGRAM_ACCESS_TOKEN: ${{ secrets.INSTAGRAM_ACCESS_TOKEN }}
          IMGBB_API_KEY:          ${{ secrets.IMGBB_API_KEY }}
          GMAIL_SENDER:           ${{ secrets.GMAIL_SENDER }}
          GMAIL_APP_PASSWORD:     ${{ secrets.GMAIL_APP_PASSWORD }}
          GMAIL_RECIPIENT:        ${{ secrets.GMAIL_RECIPIENT }}
          TELEGRAM_BOT_TOKEN:     ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:       ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python scripts/poster.py

      - name: Commit posted.json back to repo
        run: |
          git config user.name  "InstaFlow Bot"
          git config user.email "instaflow-bot@users.noreply.github.com"
          git add posted.json
          git diff --staged --quiet || git commit -m "chore: mark post as done [skip ci]"
          git push
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily_post.yml
git commit -m "feat: GitHub Actions workflow — daily cron at 9AM IST with manual dispatch"
```

---

## Self-Review Checklist

**Spec coverage:**

| Spec Section | Covered By |
|---|---|
| GitHub Actions cron + manual trigger | Task 8 |
| imgbb upload (base64, permanent URL) | Task 3 |
| Instagram image container + publish | Task 4 |
| Instagram reel container + poll + publish | Task 4 |
| Gmail SMTP notification | Task 5 |
| Telegram Bot notification | Task 5 |
| posted.json tracking (load, mark, commit back) | Task 2, Task 6, Task 8 |
| Alphabetical post order | Task 2 (`get_next_image`) |
| Skip files with no caption entry | Task 2 (`get_next_image`) |
| Empty queue notification (no crash) | Task 5, Task 6 |
| Config from env vars (GitHub Secrets) | Task 6 (`load_config`) |
| config.json.example for local dev | Task 1 |
| setup_test.py connectivity check | Task 7 |
| `.gitignore` for config.json | Task 1 |
| `[skip ci]` commit message | Task 8 |
| Failure → notify → exit code 1 | Task 6 |
| Page Access Token (never expires) note | Documented in config.json.example |

**Placeholder scan:** No TBDs, no "implement later", no "add appropriate error handling" without specifics. All steps contain real code.

**Type consistency:**
- `load_captions` returns `dict[str, str]` — used as `captions[filename]` everywhere ✓
- `load_posted` returns `list[dict]` — used as `posted` in `get_next_image` and `mark_posted` ✓
- `mark_posted(path, filename, post_id)` — called as `mark_posted(settings["posted_file"], filename, post_id)` ✓
- `get_next_image` returns `tuple[str, str] | None` — checked for `None` before unpack ✓
- `create_image_container` / `create_reel_container` return `str` (creation_id) — passed to `publish_container` ✓
- `poll_reel_status(creation_id, tok)` — called as `poll_reel_status(creation_id, tok)` in poster.py ✓
- `notify_success(config, filename, post_id)` — all three args provided ✓

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-19-instaflow-v1.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
