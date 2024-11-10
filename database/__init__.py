import aiosqlite

from lib.logger import logger
from lib.ctf_model import CTFModel


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_ctf(self, ctf: CTFModel) -> None:
        """
        Add a CTF to the database.
        """
        await self.connection.execute(
            "INSERT INTO ctf (name, description, text_channel_id, event_id, role_id, msg_id) VALUES (?, ?, ?, ?, ?,?)",
            (
                ctf.name,
                ctf.description,
                ctf.text_channel_id,
                ctf.event_id,
                ctf.role_id,
                ctf.msg_id,
            ),
        )
        await self.connection.commit()
        pass

    async def get_ctf_by_name(self, name: str) -> CTFModel:
        """
        Get a CTF from the database.
        """
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")
            return CTFModel(
                name=row[1],
                description=row[2],
                text_channel_id=row[3],
                event_id=row[4],
                role_id=row[5],
                msg_id=row[6],
            )

    async def get_ctf_by_message_id(self, message_id: int) -> CTFModel:
        """
        Get a CTF from the database.
        """
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE msg_id = ?", (message_id,)
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")
            return CTFModel(
                name=row[1],
                description=row[2],
                text_channel_id=row[3],
                event_id=row[4],
                role_id=row[5],
                msg_id=row[6],
            )

    async def is_ctf_present(self, name: str) -> bool:
        async with self.connection.execute(
            "SELECT * FROM ctf WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            logger.debug(f"{row=}")
            if row is None:
                return False
            return True
