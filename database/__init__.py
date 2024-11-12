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
        Add a server to the database.
        """
        try:
            await self.connection.execute(
                "INSERT INTO server (id, active_category_id, archive_category_id) VALUES (?,?,?)",
                (
                    server_model.id,
                    server_model.active_category_id,
                    server_model.archive_category_id,
                ),
            )
            await self.connection.commit()
        except aiosqlite.Error as e:
            logger.error(f"Error: {e}")
            return False
        else:
            return True

    async def get_server_by_id(self, server_id: int) -> ServerModel | None:
        """Get a server from the database."""
        async with self.connection.execute("SELECT * FROM server WHERE id = ?", (server_id,)) as cursor:
            row = await cursor.fetchone()
            return ServerModel(
                id=row[0],
                active_category_id=row[1],
                archive_category_id=row[2],
            )

    async def edit_category(self, server_model: ServerModel) -> bool:
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
