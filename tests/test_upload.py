import base64
import os
from unittest.mock import MagicMock, patch

import pytest
import requests as req
from scripts.upload import upload_to_imgbb


def test_upload_returns_url_on_success(tmp_path):
    path = tmp_path / "test.jpg"
    path.write_bytes(b"fake image data")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "data": {"url": "https://i.ibb.co/abc/test.jpg"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("scripts.upload.requests.post", return_value=mock_response):
        url = upload_to_imgbb("fake_api_key", str(path))

    assert url == "https://i.ibb.co/abc/test.jpg"


def test_upload_sends_base64_encoded_image(tmp_path):
    content = b"pixel data"
    path = tmp_path / "test.jpg"
    path.write_bytes(content)
    expected_b64 = base64.b64encode(content).decode("utf-8")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "data": {"url": "https://i.ibb.co/abc/test.jpg"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("scripts.upload.requests.post", return_value=mock_response) as mock_post:
        upload_to_imgbb("mykey", str(path))

    sent_data = mock_post.call_args.kwargs["data"]
    assert sent_data["image"] == expected_b64
    assert sent_data["key"] == "mykey"


def test_upload_raises_on_api_failure(tmp_path):
    path = tmp_path / "test.jpg"
    path.write_bytes(b"fake image data")

    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False, "error": {"message": "Invalid key"}}
    mock_response.raise_for_status = MagicMock()

    with patch("scripts.upload.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="imgbb upload failed"):
            upload_to_imgbb("bad_key", str(path))


def test_upload_raises_on_http_error(tmp_path):
    path = tmp_path / "test.jpg"
    path.write_bytes(b"fake image data")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = req.HTTPError("500 Server Error")

    with patch("scripts.upload.requests.post", return_value=mock_response):
        with pytest.raises(req.HTTPError):
            upload_to_imgbb("mykey", str(path))
