from dataclasses import dataclass, field


@dataclass
class User:
    name: str = field(default="")
    karma: int = field(default=0)
