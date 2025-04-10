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
    ctftime_url: str
    ctfd: bool
    team_name: str


@dataclass(frozen=True)
class ServerModel:
    """Server model class"""

    id: int
    active_category_id: int
    archive_category_id: int
    role_manager_id: int

@dataclass(frozen=True)
class ReportModel:
    """Report model class"""

    ctf_id: int
    place: int
    solves: int
    score: int
