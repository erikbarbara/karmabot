from dataclasses import dataclass, field


@dataclass
class Event:
    bot_id: str = field(default="")
    channel: str = field(default="")
    type: str = field(default="")
    subtype: str = field(default="")
    text: str = field(default="")
    user: str = field(default="")
    ts: str = field(default="")
