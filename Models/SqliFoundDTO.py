import json
from enum import Enum


class SqliType(Enum):
    ERROR = 1,
    TIME = 2


class SqliFoundDTO:
    def __init__(self, url: str, sqli_type: SqliType):
        self.url = url
        self.sqli_type = sqli_type

    @property
    def url(self):
        return self.url

    @property
    def sqli_type(self):
        return self.sqli_type

