import datetime
import io
import random
import re
from pathlib import Path

import aiofiles
import aiohttp
from PIL import Image

from lib.logger import logger

BASE_URL = "https://ctftime.org/api/v1"
HTTP_STATUS_OK = 200
MAX_LENGTH = 100
MIN_LENGTH = 8


USER_AGENT_LIST = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Windows; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8",
    "Mozilla/5.0 (Windows NT 10.0; Windows; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Windows; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
]


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
                session.get(url, headers={"User-Agent": random.choice(USER_AGENT_LIST)}) as response,  # noqa: S311
            ):
                if response.status == HTTP_STATUS_OK:
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


async def get_ctf_info(ctftime_id: int) -> dict | None:
    """
    Get the information of a CTF from ctftime.org.

    Args:
        ctftime_id (int): The ID of the CTF.

    Returns:
        dict: The information of the CTF.

    """
    logger.debug(f"Getting information for event with ID {ctftime_id}")
    logger.debug(f"GET {BASE_URL}/events/{ctftime_id}/")

    async with (
        aiohttp.ClientSession() as session,
        session.get(f"{BASE_URL}/events/{ctftime_id}/", headers={"User-Agent": random.choice(USER_AGENT_LIST)}) as response,  # noqa: S311
    ):
        logger.debug(f"Response status code: {response.status}")
        response_text = await response.text()
        logger.debug(f"Response data: {response_text}")

        if response.status == HTTP_STATUS_OK:
            return await response.json()
        logger.error(f"Failed to retrieve CTF information. Status code: {response.status}")
        return None

async def get_ctfs() -> list[dict] | None:
    """
    Get the list of CTFs from ctftime.org.

    Returns:
        list[dict]: The list of CTFs.

    """
    logger.debug("Getting list of CTFs")
    logger.debug(f"GET {BASE_URL}/events/")

    async with (
        aiohttp.ClientSession() as session,
        session.get(
            f"{BASE_URL}/events/",
            headers={"User-Agent": random.choice(USER_AGENT_LIST)},
            params={
                "limit": 10,
                "start": int(datetime.datetime.now(datetime.UTC).timestamp()),
                "finish": int((datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)).timestamp()),
            },
        ) as response,
    ):
        logger.debug(f"Response status code: {response.status}")
        response_text = await response.text()
        logger.debug(f"Response data: {response_text}")

        if response.status == HTTP_STATUS_OK:
            return await response.json()
        logger.error(f"Failed to retrieve CTFs. Status code: {response.status}")
        return None


def sanitize_input(inp: str) -> str:
    """
    Sanitize the input.

    Args:
        inp (str): The input to sanitize.

    Returns:
        str: The sanitized input.

    """
    inp = inp.strip()
    return re.sub(r"[^a-zA-Z0-9-_|\s]", "", inp)


def normalize_url_ctf(url: str) -> str:
    """
    Normalize the URL of a CTF.

    Args:
        url (str): The URL to normalize.

    Returns:
        str: The normalized URL.

    """
    if url.endswith("/"):
        url = url.removesuffix("/")

    url_without_protocol = url.removeprefix("http://").removeprefix("https://")
    if "/" in url_without_protocol:
        url_without_protocol = url_without_protocol.split("/")[0]
    return url.split("://")[0] + "://" + url_without_protocol


def get_categories(solves: list[dict]) -> list[str]:
    """
    Get all unique categories from the solves.

    Args:
        solves (list[dict]): The list of solves.

    Returns:
        list[str]: A list of unique categories.

    """
    return list({solve["challenge"]["category"] for solve in solves})


async def get_results_info(ctftime_id: int, year: int, team_id: int) -> dict | None:
    """
    Get the results information of a CTF from ctftime.org.

    Args:
        ctftime_id (int): The ID of the CTF.
        year (int): The year of the CTF.
        team_id (int): The ID of the team.

    Returns:
        dict: The results information of the CTF.

    """
    logger.debug(f"Getting results for event with ID {ctftime_id}")
    logger.debug(f"GET {BASE_URL}/results/{year}")

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(f"{BASE_URL}/results/{year}/", headers={"User-Agent": random.choice(USER_AGENT_LIST)}) as response,  # noqa: S311
        ):
            logger.debug(f"Response status code: {response.status}")
            if response.status == HTTP_STATUS_OK:
                response_data = await response.json()
                response_data = response_data[str(ctftime_id)]["scores"]
                for result in response_data:
                    if result["team_id"] == team_id:
                        return result
            logger.error(f"Failed to retrieve CTF results information. Status code: {response.status}")
    except (KeyError, aiohttp.ClientError, ValueError) as e:
        logger.error(f"Error while retrieving CTF results information: {e}")
    return None
