from dataclasses import dataclass


@dataclass(frozen=True)
class CTFModel:
    """CTF model class"""

    id: int
    server_id: int
    name: str
    description: str
    text_channel_id: int
    event_id: int
    role_id: int
    msg_id: int
    ctftime_id: int



@dataclass(frozen=True)
class ServerModel:
    """Server model class"""

    id: int
    active_category_id: int
    archive_category_id: int
    role_manager_id: int
    feed_channel_id: int
    team_id: int

@dataclass(frozen=True)
class ReportModel:
    """Report model class"""

    ctf_id: int
    place: int
    solves: int
    score: int

@dataclass(frozen=True)
class Creds:
    """Credentials model class"""

    id: int
    ctf_id: int
    username: str
    password: str
    personal: bool
