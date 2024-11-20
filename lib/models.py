from dataclasses import dataclass


@dataclass(frozen=True)
class CTFModel:
    """CTF model class"""

    server_id: int
    name: str
    description: str
    text_channel_id: int
    event_id: int
    role_id: int
    msg_id: int


@dataclass(frozen=True)
class ServerModel:
    """Server model class"""

    id: int
    active_category_id: int
    archive_category_id: int
    role_manager_id: int
