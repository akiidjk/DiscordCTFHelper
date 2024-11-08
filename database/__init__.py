import aiosqlite

from lib.ctf_model import CTFModel


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def add_ctf(self, ctf: CTFModel) -> None:
        """
        Add a CTF to the database.
        """
        await self.connection.execute(
            "INSERT INTO ctf (name, description, text_channel_id, event_id, role_id) VALUES (?, ?, ?, ?, ?)",
            (ctf.name, ctf.description, ctf.text_channel_id, ctf.event_id, ctf.role_id),
        )
        await self.connection.commit()
        pass
