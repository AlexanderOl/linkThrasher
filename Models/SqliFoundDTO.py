import json
from enum import Enum


class SqliType(Enum):
    ERROR = 1,
    TIME = 2,
    FORM_ERROR = 3,
    FORM_GET_ERROR = 3,


class SqliFoundDTO:
    def __init__(self, sqli_type: SqliType, url: str, payload, web_page, header_msg):
        self._url = url
        self._sqli_type = sqli_type
        self._payload = payload
        self._web_page = web_page
        self._response_length = len(web_page)
        self._header_msg = header_msg

    @property
    def url(self):
        return self._url

    @property
    def sqli_type(self):
        return self._sqli_type

    @property
    def response_length(self):
        return self._response_length

    def __str__(self):
        return f'url: {self._url}, sqliType: {self._sqli_type}, details: {self._header_msg}'
