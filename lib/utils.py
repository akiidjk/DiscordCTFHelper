import io
import re
import requests
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
    if url is not None and url != "":
        try:
            response = requests.get(url, headers={"User-Agent": "CookieBot"})
            response.raise_for_status()

            with Image.open(io.BytesIO(response.content)) as pillow_img:
                if pillow_img.format != "PNG":
                    image_buffer = io.BytesIO()
                    pillow_img.save(image_buffer, format="PNG")
                    return image_buffer.getvalue()
                else:
                    return response.content
        except Exception as e:
            logger.error(f"Error: {e}")
            return open("images/default.png", "rb").read()
    else:
        return open("images/default.png", "rb").read()


def check_url(url: str) -> bool:
    """
    Check if the URL is valid.

    :param url: The URL to check.
    :return: True if the URL is valid, False otherwise.
    """
    return bool(re.match(r"^https://ctftime.org/event/\d+$", url))


def get_ctf_info(url: str) -> dict:
    """
    Get the information of a CTF from ctftime.org.

    :param url: The URL of the CTF.
    :return: The information of the CTF.
    """
    if url.endswith("/"):
        url = url[:-1]
    id_event = url.split("/")[-1]
    logger.debug(f"Getting information for event with ID {id_event}")
    logger.debug(f"GET {BASE_URL}/events/{id_event}/")
    response = requests.get(
        f"{BASE_URL}/events/{id_event}/", headers={"User-Agent": "CookieBot"}
    )
    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response data: {response.text}")
    return response.json()
