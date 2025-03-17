import asyncio
import threading

import discord
import requests
from bs4 import BeautifulSoup

from lib.logger import logger


class CTFd:
    def __init__(self, ctf_url):
        """
        Initialize the CTFd API wrapper.

        Args:
            ctf_url (str): The base URL of the CTF platform.

        """
        self.ctf_url = ctf_url.rstrip("/")
        self.session = requests.Session()

    def _get(self, endpoint) -> dict | None | str:
        """Helper function to make GET requests with error handling."""
        try:
            response = self.session.get(self.ctf_url + endpoint)
            response.raise_for_status()
            return response.json() if "application/json" in response.headers.get("Content-Type", "") else response.text
        except requests.exceptions.RequestException as err:
            logger.error(f"GET {endpoint} failed: {err}")
            return None

    def _post(self, endpoint, data) -> dict | None | str:
        """Helper function to make POST requests with error handling."""
        try:
            response = self.session.post(self.ctf_url + endpoint, data=data, allow_redirects=False)
            response.raise_for_status()
            return response.json() if "application/json" in response.headers.get("Content-Type", "") else response.text
        except requests.exceptions.RequestException as err:
            logger.error(f"POST {endpoint} failed: {err}")
            return None

    def get_scoreboard(self) -> dict | None | str:
        """Retrieve the CTF scoreboard."""
        return self._get("/api/v1/scoreboard")

    def get_team(self, team_id: int) -> dict | None | str:
        """Retrieve information about a specific team."""
        return self._get(f"/api/v1/teams/{team_id}")

    def get_team_solves(self, team_id: int) -> dict | None | str:
        """Retrieve the solve history of a team."""
        return self._get(f"/api/v1/teams/{team_id}/solves")

    def get_team_id_by_name(self, team_name: str) -> int | None:
        """Retrieve the team ID by its name."""
        teams = self._get("/api/v1/teams")
        logger.debug(f"Teams: {teams}")
        if teams and "data" in teams and isinstance(teams, dict):
            for team in teams["data"]:
                if team["name"] == team_name:
                    return team["id"]
        return None

    def get_nonce(self) -> str | None:
        """Retrieve the CSRF nonce required for authentication actions."""
        response_text = self._get("/register")
        if response_text:
            soup = BeautifulSoup(response_text, "html.parser")
            nonce_element = soup.find("input", {"id": "nonce"})
            return nonce_element["value"] if nonce_element else None
        return None

    def register(self, username, email, password):
        """Register a new user."""
        nonce = self.get_nonce()
        if nonce:
            data = {"name": username, "email": email, "password": password, "nonce": nonce}
            response = self._post("/register", data)
            if response:
                logger.info("Registration successful")
                return True
        logger.error("Registration failed")
        return False

    def login(self, username, password):
        """Login a user."""
        nonce = self.get_nonce()
        if nonce:
            data = {"name": username, "password": password, "nonce": nonce}
            response = self._post("/login", data)
            if response:
                logger.info("Login successful")
                logger.debug(f"Cookies: {self.session.cookies}")
                return True
        logger.error("Login failed")
        return False

    def logout(self):
        """Logout the current user."""
        response = self._get("/logout")
        if response:
            logger.info("Logout successful")
            return True
        logger.error("Logout failed")
        return False


class CTFdNotifier:
    """Send notifications to the user."""

    def __init__(self, ctfd, team_id: int, channel: discord.TextChannel):
        self.ctfd = ctfd
        self.channel = channel
        self.team_id = team_id
        self.running = True

        self.loop = asyncio.get_event_loop()

        self.thread = threading.Thread(target=self._run_observer_loop, daemon=True)
        self.thread.start()

    def _run_observer_loop(self):
        """Run the observer loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.observer())
        loop.close()

    async def observer(self):
        """Observe changes"""
        old_l = 0
        while self.running:
            logger.debug("Observer loop running...")
            solves = self.ctfd.get_team_solves(self.team_id)
            logger.debug(f"Solves: {solves}")
            if not isinstance(solves, dict):
                logger.error("Invalid response from CTFd")
                await asyncio.sleep(60)
                continue

            solves = solves.get("data", [])
            actual_l = len(solves)
            logger.debug(f"Actual length: {actual_l}")
            logger.debug(f"Old length: {old_l}")
            n_new_solves = actual_l - old_l
            logger.debug(f"Number of new solves: {n_new_solves}")
            for i in range(n_new_solves):
                new_solve = solves[i]
                challenge = new_solve.get("challenge", {})
                user = new_solve.get("user", {})

                message = f"**New solve**: ``{challenge.get('category')}::{challenge.get('name')}`` **by** ``{user.get('name')}`` 🍪"
                logger.debug(f"Message: {message}")
                asyncio.run_coroutine_threadsafe(self.channel.send(message), self.loop)

            old_l = actual_l
            await asyncio.sleep(60)

    def stop_thread(self):
        """Stop the thread."""
        self.running = False
        self.thread.join()
