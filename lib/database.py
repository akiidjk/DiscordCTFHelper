from lib.models import Creds
import aiosqlite

from lib.logger import logger
from lib.models import CTFModel, ReportModel, ServerModel


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_creds(self, username: str, password: str, personal: bool, ctf_id: int) -> None:
        """
        Add or update credentials in the database.
        If credentials with the same ctf_id exist, update them; otherwise, insert new ones.
        """
        async with self.connection.execute(
            """SELECT 1 FROM creds WHERE ctf_id = ?""",
            (ctf_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            await self.connection.execute(
                """UPDATE creds
                SET username = ?, password = ?, personal = ?
                WHERE ctf_id = ?""",
                (
                    username,
                    password,
                    personal,
                    ctf_id,
                ),
            )
        else:
            await self.connection.execute(
                """INSERT INTO creds
                (username, password, personal, ctf_id)
                VALUES (?, ?, ?, ?)""",
                (
                    username,
                    password,
                    personal,
                    ctf_id,
                ),
            )
        await self.connection.commit()

    async def get_creds(self, ctf_id: int):
        """
        Get credentials from the database.

        Args:
            ctf_id (int): The ID of the CTF.
        Returns:
            list[tuple[str, str]]: A list of tuples containing the username and password.
        """
        creds = []
        async with self.connection.execute(
            """SELECT username, password, personal
            FROM creds WHERE ctf_id = ?""",
            (ctf_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                creds.append(Creds(
                    id=0,
                    ctf_id=ctf_id,
                    username=row[0],
                    password=row[1],
                    personal=bool(row[2]),
                ))
        return creds

    async def add_report(self, report: ReportModel) -> None:
        """
        Add a report to the database.
        """
        await self.connection.execute(
            """INSERT INTO report
            (ctf_id, place, solves, score)
            VALUES (?, ?, ?, ?)""",
            (
                report.ctf_id,
                report.place,
                report.solves,
                report.score,
            ),
        )
        await self.connection.commit()

    async def get_report(self, ctf_id: int) -> ReportModel | None:
        """
        Get a report from the database.

        Args:
            ctf_id (int): The ID of the CTF.

        Returns:
            Optional[ReportModel]: The report or None if not found.

        """
        async with self.connection.execute(
            """SELECT ctf_id, place, solves, score
            FROM report WHERE ctf_id = ?""",
            (ctf_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return ReportModel(*row)


    async def update_report(self, ctf_id: int, report: ReportModel):
        """
        Update a report in the database. If it does not exist, create it.

        Args:
            ctf_id (int): The ID of the CTF.
            report (ReportModel): The report to update.

        Returns:
            None

        """
        await self.connection.execute(
                """UPDATE report
                SET place = ?, solves = ?, score = ?
                WHERE ctf_id = ?""",
                (
                    report.place,
                    report.solves,
                    report.score,
                    ctf_id,
                ),
            )
        await self.connection.commit()

    async def add_ctf(self, ctf: CTFModel) -> None:
        """
        Add a CTF to the database.
        """
        await self.connection.execute(
            """INSERT INTO ctf
            (server_id, name, description, text_channel_id, event_id, role_id, msg_id, ctftime_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ctf.server_id,
                ctf.name,
                ctf.description,
                ctf.text_channel_id,
                ctf.event_id,
                ctf.role_id,
                ctf.msg_id,
                ctf.ctftime_id,
            ),
        )
        await self.connection.commit()

    async def get_ctf_by_name(self, name: str, server_id: int) -> CTFModel | None:
        """
        Get a CTF from the database.

        Args:
            name (str): The name of the CTF.
            server_id (int): The server ID.

        Returns:
            Optional[CTFModel]: The CTF or None if not found.

        """
        logger.debug(f"{name=}, {server_id=}")
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE name = ? AND server_id = ?",
            (
                name,
                server_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")

            if row is None:
                return None

            return CTFModel(
                id=row[0],
                server_id=row[1],
                name=row[2],
                description=row[3],
                text_channel_id=row[4],
                event_id=row[5],
                role_id=row[6],
                msg_id=row[7],
                ctftime_id=row[8],
            )

    async def get_ctf_by_id(self, ctf_id: int) -> CTFModel | None:
        """
        Get a CTF from the database.

        Args:
            id (int): The database id of the CTF.

        Returns:
            Optional[CTFModel]: The CTF or None if not found.

        """
        logger.debug(f"{ctf_id=}")
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE id = ?",
            (
                ctf_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")

            if row is None:
                return None

            return CTFModel(
                id=row[0],
                server_id=row[1],
                name=row[2],
                description=row[3],
                text_channel_id=row[4],
                event_id=row[5],
                role_id=row[6],
                msg_id=row[7],
                ctftime_id=row[8],
            )

    async def delete_ctf(self, ctf_id: int) -> bool:
        """
        Delete a CTF from the database.

        Args:
            id (int): The database id of the CTF.

        Returns:
            bool: True if the CTF was deleted, False otherwise.

        """
        try:
            await self.connection.execute(
                "DELETE FROM ctf WHERE id = ?",
                (ctf_id,),
            )
            await self.connection.commit()
        except aiosqlite.Error as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True

    async def get_ctf_by_message_id(self, message_id: int, server_id: int) -> CTFModel | None:
        """
        Get a CTF from the database.

        Args:
            message_id (int): The message ID.
            server_id (int): The server ID.

        Returns:
            Optional[CTFModel]: The CTF or None if not found.

        """
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE msg_id = ? AND server_id = ?",
            (
                message_id,
                server_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")
            if row is None:
                return None

            return CTFModel(
                id=row[0],
                server_id=row[1],
                name=row[2],
                description=row[3],
                text_channel_id=row[4],
                event_id=row[5],
                role_id=row[6],
                msg_id=row[7],
                ctftime_id=row[8],
            )

    async def get_ctf_by_channel_id(self, channel_id: int, server_id: int) -> CTFModel | None:
        """
        Get a CTF from the database.

        Args:
            channel_id (int): The text channel ID.
            server_id (int): The server ID.

        Returns:
            Optional[CTFModel]: The CTF or None if not found.

        """
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE text_channel_id = ? AND server_id = ?",
            (
                channel_id,
                server_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")
            if row is None:
                return None

            return CTFModel(
                id=row[0],
                server_id=row[1],
                name=row[2],
                description=row[3],
                text_channel_id=row[4],
                event_id=row[5],
                role_id=row[6],
                msg_id=row[7],
                ctftime_id=row[8],
            )

    async def is_ctf_present(self, name: str, server_id: int) -> bool:
        """
        Check if a CTF is present in the database.

        Args:
            name (str): name of the CTF
            server_id (int): The server ID.

        Returns:
            bool: True if the CTF is present, False otherwise.

        """
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE name = ? AND server_id = ?",
            (
                name,
                server_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")
            return row is not None

    async def add_server(self, server_model: ServerModel) -> bool:
        """
        Add a server to the database

        Args:
            server_model (ServerModel): The server model to add.

        Returns:
            bool: True if the server was added, False otherwise.

        """
        try:
            await self.connection.execute(
                "INSERT INTO server (id, active_category_id, archive_category_id, role_manager_id, feed_channel_id,team_id) VALUES (?,?,?,?,?,?)",
                (
                    server_model.id,
                    server_model.active_category_id,
                    server_model.archive_category_id,
                    server_model.role_manager_id,
                    server_model.feed_channel_id,
                    server_model.team_id
                ),
            )
            await self.connection.commit()
        except aiosqlite.Error as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True

    async def get_server_by_id(self, server_id: int) -> ServerModel | None:
        """
        Get a server from the database.

        Args:
            server_id (int): The server ID.

        Returns:
            Optional[ServerModel]: The server or None if not found.

        """
        async with self.connection.execute("SELECT * FROM server WHERE id = ?", (server_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return ServerModel(
                id=row[0],
                active_category_id=row[1],
                archive_category_id=row[2],
                role_manager_id=row[3],
                feed_channel_id=row[4],
                team_id=row[5],
            )

    async def edit_category(self, server_model: ServerModel) -> bool:
        """
        Edit the category of a server

        Args:
            server_model (ServerModel): The server model to edit.

        Returns:
            bool: True if the category was edited, False otherwise.

        """
        try:
            await self.connection.execute(
                "UPDATE server SET active_category_id = ?, archive_category_id = ? WHERE id = ?",
                (
                    server_model.active_category_id,
                    server_model.archive_category_id,
                    server_model.id,
                ),
            )
            await self.connection.commit()
        except aiosqlite.Error as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True

    async def delete_server(self, server_id: int) -> bool:
        """
        Delete a server from the database

        Args:
            server_id: The server ID.

        Returns:
            bool: True if the server was deleted, False otherwise.

        """
        try:
            await self.connection.execute(
                "DELETE FROM server WHERE id = ?",
                (server_id,),
            )
            await self.connection.commit()
        except aiosqlite.Error as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True


    async def get_ctfs_list(self, server_id: int) -> list[CTFModel]:
        """
        Get a list of CTFs from the database.

        Args:
            server_id (int): The server ID.

        Returns:
            list[CTFModel]: A list of CTFs.

        """
        ctfs: list[CTFModel] = []
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE server_id = ?",
            (server_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                ctfs.append(
                    CTFModel(
                        id=row[0],
                        server_id=row[1],
                        name=row[2],
                        description=row[3],
                        text_channel_id=row[4],
                        event_id=row[5],
                        role_id=row[6],
                        msg_id=row[7],
                        ctftime_id=row[8],
                    )
                )
        return ctfs
