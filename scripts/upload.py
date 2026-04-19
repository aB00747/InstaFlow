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
