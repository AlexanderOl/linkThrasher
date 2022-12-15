import json
from enum import Enum


class SqliType(Enum):
    ERROR = 1,
    TIME = 2


class SqliFoundDTO:
    def __init__(self, url: str, sqli_type: SqliType):
        self._url = url
        self._sqli_type = sqli_type

    @property
    def url(self):
        return self._url

    @property
    def sqli_type(self):
        return self._sqli_type

    def __str__(self):
        return f'url: {self._url}, sqliType: {self._sqli_type}'
