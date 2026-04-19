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
            raise RuntimeError("Reel processing failed with status: ERROR")
        time.sleep(interval)
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
