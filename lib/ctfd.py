import asyncio
import datetime
import threading

import discord
import requests
from bs4 import BeautifulSoup, Tag

from lib.logger import logger


class CTFd:
    def __init__(self, ctf_url):
        self.ctf_url = ctf_url.rstrip("/")
        self.session = requests.Session()
        logger.info(f"CTFd API initialized with URL: {self.ctf_url}")

    def _get(self, endpoint) -> dict | None | str:
        try:
            response = self.session.get(self.ctf_url + endpoint)
            response.raise_for_status()
            logger.debug(f"GET {endpoint} successful: {response.status_code}")
            return response.json() if "application/json" in response.headers.get("Content-Type", "") else response.text
        except requests.exceptions.RequestException as err:
            logger.error(f"GET {endpoint} failed: {err}")
            return None

    def _post(self, endpoint, data) -> dict | None | str:
        try:
            response = self.session.post(self.ctf_url + endpoint, data=data, allow_redirects=False)
            response.raise_for_status()
            logger.debug(f"POST {endpoint} successful: {response.status_code}")
            return response.json() if "application/json" in response.headers.get("Content-Type", "") else response.text
        except requests.exceptions.RequestException as err:
            logger.error(f"POST {endpoint} failed: {err}")
            return None

    def get_team(self, team_id: int) -> dict | None | str:
        """Retrieve information about a specific team."""
        result = self._get(f"/api/v1/teams/{team_id}")
        if isinstance(result, dict) and result.get("success"):
            return result.get("data")

        logger.error(f"GET /api/v1/teams/{team_id} failed: {result}")
        return None

    def get_team_solves(self, team_id: int) -> dict | None | str:
        """Retrieve the solve history of a team."""
        result = self._get(f"/api/v1/teams/{team_id}/solves")
        if isinstance(result, dict) and result.get("success"):
            return result.get("data")

        logger.error(f"GET /api/v1/teams/{team_id}/solves failed: {result}")
        return None

    def get_team_id_by_name(self, team_name: str) -> int | None:
        logger.info(f"Fetching team ID for: {team_name}")
        teams_response = self._get("/api/v1/teams")
        if not teams_response or not isinstance(teams_response, dict):
            logger.error("Failed to retrieve teams for team ID lookup.")
            return None

        meta = teams_response.get("meta", {})
        pagination = meta.get("pagination", {})
        n_pages = pagination.get("pages", 0)

        for page in range(1, n_pages + 1):
            logger.debug(f"Fetching teams from page {page}...")
            teams = self._get(f"/api/v1/teams?page={page}")
            if teams and isinstance(teams, dict):
                data = teams.get("data", [])
                for team in data:
                    if team.get("name") == team_name:
                        logger.info(f"Found team {team_name} with ID {team.get('id')}")
                        return team.get("id")

        logger.warning(f"Team {team_name} not found.")
        return None

    def get_nonce(self) -> str | None:
        """Retrieve the CSRF nonce required for authentication actions."""
        response_text = self._get("/register")
        if isinstance(response_text, str):
            soup = BeautifulSoup(response_text, "html.parser")
            nonce_element = soup.find("input", {"id": "nonce"})
            logger.debug(type(nonce_element))
            if isinstance(nonce_element, Tag):
                return str(nonce_element.get("value", ""))
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
        else:
            logger.error("Failed to retrieve nonce")
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
        else:
            logger.error("Failed to retrieve nonce")
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
    def __init__(self, ctfd, team_id: int, channel: discord.TextChannel, role: discord.Role | None = None):
        self.ctfd = ctfd
        self.channel = channel
        self.team_id = team_id
        self.role = role
        self.running = True
        self.loop = asyncio.get_event_loop()
        self.thread = threading.Thread(target=self._run_observer_loop, daemon=True)
        self.thread.start()
        logger.info(f"CTFdNotifier initialized for team {team_id}.")

    def _run_observer_loop(self):
        """Run the observer loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.observer())
        loop.close()

    async def observer(self):
        old_l = 0
        while self.running:
            logger.debug("Observer loop running...")
            solves = self.ctfd.get_team_solves(self.team_id)
            if not isinstance(solves, dict):
                logger.error("Invalid response from CTFd, retrying in 60s.")
                await asyncio.sleep(60)
                continue

            solves = solves.get("data", [])
            actual_l = len(solves)
            n_new_solves = actual_l - old_l

            logger.debug(f"Total solves: {actual_l}, New solves: {n_new_solves}")

            for i in range(n_new_solves):
                new_solve = solves[i]
                challenge = new_solve.get("challenge", {})
                user = new_solve.get("user", {})
                time_solve = new_solve.get("date", datetime.datetime.now(tz=datetime.UTC))
                if isinstance(time_solve, str):
                    time_solve = datetime.datetime.strptime(time_solve, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC)

                message = (
                    f"🏴 Flagged ``{challenge.get('name')}`` ({challenge.get('category')}) "
                    f"by **@{user['name']}** | 🕒 {time_solve.strftime('%H:%M')} | "
                    f"{self.role.mention if self.role else f'@{user["name"]}'}"
                )

                logger.info(f"New solve detected: {message}")
                asyncio.run_coroutine_threadsafe(self.channel.send(message), self.loop)

            old_l = actual_l
            await asyncio.sleep(60)

    def stop_thread(self):
        """Stop the thread."""
        self.running = False
        self.thread.join()
