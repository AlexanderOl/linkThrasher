from enum import Enum


class SstiType(Enum):
    Get = 1,
    PostForm = 2,
    GetForm = 3


class SstiFoundDTO:
    def __init__(self, url: str, ssti_type: SstiType, payload, web_page, header_msg):
        self._url = url
        self._ssti_type = ssti_type
        self._payload = payload
        self._web_page = web_page
        self._header_msg = header_msg

    @property
    def url(self):
        return self._url

    @property
    def ssti_type(self):
        return self._ssti_type

    @property
    def web_page(self):
        return self._web_page

    def __str__(self):
        return f'url: {self._url}, ssti_type: {self._ssti_type}, details: {self._header_msg}'
