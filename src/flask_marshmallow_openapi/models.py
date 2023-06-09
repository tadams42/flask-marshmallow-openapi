import enum
from dataclasses import asdict, dataclass


class Securities(enum.Enum):
    access_token = 1
    refresh_token = 2
    no_token = 3


class ParameterLocation(enum.Enum):
    query = 1
    header = 2
    path = 3
    cookie = 4


@dataclass
class ParameterObject:
    name: str
    in_: ParameterLocation
    description: str = ""
    required: bool = False
    deprecated: bool = False
    allow_empty_value: bool = True

    @property
    def to_dict(self) -> dict[str, str]:
        retv = asdict(self)
        del retv["in_"]
        retv["in"] = self.in_.name
        retv["schema"] = {"type": "string"}
        return retv
