from dataclasses import dataclass


@dataclass(frozen=True)
class CTFModel:
    """CTF model class"""

    name: str
    description: str
    text_channel_id: int
    event_id: int
    role_id: int
    msg_id: int
