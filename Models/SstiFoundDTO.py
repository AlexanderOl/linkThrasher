from enum import Enum


class SstiType(Enum):
    Get = 1,
    PostForm = 2,
    GetForm = 3


class SstiFoundDTO:
    def __init__(self, url: str, ssti_type: SstiType, payload, web_page):
        self._url = url
        self._ssti_type = ssti_type
        self._payload = payload
        self._web_page = web_page

    def url(self):
        return self._url

    def ssti_type(self):
        return self._ssti_type

    def web_page(self):
        return self._web_page

    def __str__(self):
        return f'url: {self._url}, payload: {self._payload}'
