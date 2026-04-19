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
