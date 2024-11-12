import io
import re
from pathlib import Path

import aiofiles
import aiohttp
from PIL import Image

from lib.logger import logger

BASE_URL = "https://ctftime.org/api/v1"


async def get_logo(url: str) -> bytes:
    """
    Get the logo of the CTF.

    Args:
        url (str): The URL of the logo.

    Returns:
        bytes: The logo of the CTF.

    """
    if url:
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers={"User-Agent": "CookieBot"}) as response,
            ):
                if response.status == 200:
                    content = await response.read()
                    with Image.open(io.BytesIO(content)) as pillow_img:
                        if pillow_img.format != "PNG":
                            image_buffer = io.BytesIO()
                            pillow_img.save(image_buffer, format="PNG")
                            return image_buffer.getvalue()

                        return content
                else:
                    logger.error(f"Failed to retrieve image. Status code: {response.status}")
        except (OSError, aiohttp.ClientError) as e:
            logger.error(f"Failed to retrieve image: {e}")

    async with aiofiles.open(Path("images/default.png"), "rb") as default_img:
        return await default_img.read()


def check_url(url: str) -> bool:
    """
    Check if the URL is valid.

    :param url: The URL to check.
    :return: True if the URL is valid, False otherwise.
    """
    return bool(re.match(r"^https://ctftime.org/event/\d+$", url))


async def get_ctf_info(url: str) -> dict | None:
    """
    Get the information of a CTF from ctftime.org.

    Args:
        url (str): The URL of the CTF.

    Returns:
        dict: The information of the CTF.

    """
    if url.endswith("/"):
        url = url[:-1]
    id_event = url.split("/")[-1]
    logger.debug(f"Getting information for event with ID {id_event}")
    logger.debug(f"GET {BASE_URL}/events/{id_event}/")

    async with (
        aiohttp.ClientSession() as session,
        session.get(f"{BASE_URL}/events/{id_event}/", headers={"User-Agent": "CookieBot"}) as response,
    ):
        logger.debug(f"Response status code: {response.status}")
        response_text = await response.text()
        logger.debug(f"Response data: {response_text}")

        if response.status == 200:  # noqa: PLR2004
            return await response.json()
        logger.error(f"Failed to retrieve CTF information. Status code: {response.status}")
        return None
