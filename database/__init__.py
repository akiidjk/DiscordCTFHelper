import aiosqlite

from lib.logger import logger
from lib.models import CTFModel, ServerModel


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_ctf(self, ctf: CTFModel) -> None:
        """
        Add a CTF to the database.
        """
        await self.connection.execute(
            "INSERT INTO ctf (server_id,name, description, text_channel_id, event_id, role_id, msg_id) VALUES (?,?, ?, ?, ?, ?,?)",
            (
                ctf.server_id,
                ctf.name,
                ctf.description,
                ctf.text_channel_id,
                ctf.event_id,
                ctf.role_id,
                ctf.msg_id,
            ),
        )
        await self.connection.commit()

    async def get_ctf_by_name(self, name: str, server_id: int) -> CTFModel:
        """
        Get a CTF from the database.

        Args:
            name (str): The name of the CTF.
            server_id (int): The server ID.

        Returns:
            CTFModel: The CTF.

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
                server_id=row[1],
                name=row[2],
                description=row[3],
                text_channel_id=row[4],
                event_id=row[5],
                role_id=row[6],
                msg_id=row[7],
            )

    async def get_ctf_by_message_id(self, message_id: int, server_id: int) -> CTFModel:
        """
        Get a CTF from the database.

        Args:
            message_id (int): The message ID.
            server_id (int): The server ID.

        Returns:
            CTFModel: The CTF.

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
                server_id=row[1],
                name=row[2],
                description=row[3],
                text_channel_id=row[4],
                event_id=row[5],
                role_id=row[6],
                msg_id=row[7],
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
                "INSERT INTO server (id, active_category_id, archive_category_id, role_manager_id) VALUES (?,?,?,?)",
                (
                    server_model.id,
                    server_model.active_category_id,
                    server_model.archive_category_id,
                    server_model.role_manager_id,
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
            ServerModel | None: The server.

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
                "UPDATE server SET active_category_id = ? AND set archive_category_id = ? WHERE id = ?",
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
