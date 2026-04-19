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
    assert mock_sleep.call_count == 2  # slept after 1st and 2nd IN_PROGRESS (not after FINISHED)


def test_poll_reel_status_raises_on_error_status():
    mock_resp = _mock_json_response({"status_code": "ERROR"})
    with patch("scripts.instagram.requests.get", return_value=mock_resp):
        with patch("scripts.instagram.time.sleep"):
            with pytest.raises(RuntimeError, match="Reel processing failed"):
                poll_reel_status("cid", "tok", timeout=60, interval=5)


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
