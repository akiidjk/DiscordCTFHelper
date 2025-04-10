import io
import random
import re
import secrets
import string
from collections import defaultdict
from pathlib import Path

import aiofiles
import aiohttp
import requests
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


def check_url(url: str) -> bool:
    """
    Check if the URL is a valid CTFTime URL.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is a valid CTFTime URL, False otherwise.

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
        url = url.removesuffix("/")
    id_event = url.split("/")[-1]
    logger.debug(f"Getting information for event with ID {id_event}")
    logger.debug(f"GET {BASE_URL}/events/{id_event}/")

    async with (
        aiohttp.ClientSession() as session,
        session.get(f"{BASE_URL}/events/{id_event}/", headers={"User-Agent": random.choice(USER_AGENT_LIST)}) as response,  # noqa: S311
    ):
        logger.debug(f"Response status code: {response.status}")
        response_text = await response.text()
        logger.debug(f"Response data: {response_text}")

        if response.status == HTTP_STATUS_OK:
            return await response.json()
        logger.error(f"Failed to retrieve CTF information. Status code: {response.status}")
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


def create_description(team_name: str, team_data: dict, solves: list[dict]) -> str:
    """
    Create a formatted description with team statistics and solve details.

    Args:
        team_name (str): The name of the team.
        team_data (dict): Team information (score, place, members).
        solves (list[dict]): List of solve data.

    Returns:
        str: The formatted description.

    """
    category_solve_counts = defaultdict(int)
    for solve in solves:
        category_solve_counts[solve["challenge"]["category"]] += 1
    category_details = "\n".join(f"- {category}: {count} solves" for category, count in category_solve_counts.items())

    return f"""
## Final statistics for {team_name}:

- Score: {team_data["score"]}
- Place: {team_data["place"]}
- Number of members: {len(team_data["members"])}

## Team solves:
- Total solves: {len(solves)}

{category_details}
"""


def random_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.

    Args:
        length (int): Length of the generated password (default: 16).

    Returns:
        str: A secure random password.

    """
    if length < MIN_LENGTH or length > MAX_LENGTH:
        error_msg = f"Password length should be between {MIN_LENGTH} and {MAX_LENGTH} characters for security reasons."
        raise ValueError(error_msg)

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_+-=.?"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def is_ctfd(url: str) -> bool:
    r = requests.get(url + "/api/v1/users",timeout=10)
    return r.status_code != requests.codes.not_found
