from enum import Enum


class XssType(Enum):
    Get = 1,
    PostForm = 2,
    GetForm = 3


class XssFoundDTO:
    def __init__(self, xss_type: XssType, url: str, payload, web_page):
        self._url = url
        self._xss_type = xss_type
        self._payload = payload
        self._web_page = web_page

    @property
    def url(self):
        return self._url

    @property
    def xss_type(self):
        return self._xss_type

    @property
    def payload(self):
        return self._payload

    @property
    def web_page(self):
        return self._web_page

    def __str__(self):
        return f'url: {self._url}, payload: {self._payload}, xss_type: {self._xss_type}'
