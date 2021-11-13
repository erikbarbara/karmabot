from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Event:
    bot_id: str = field(default="")
    channel: str = field(default="")
    type: str = field(default="")
    subtype: str = field(default="")
    text: str = field(default="")
    user: str = field(default="")
