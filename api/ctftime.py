import requests

from lib.logger import logger

BASE_URL = "https://ctftime.org/api/v1"


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
