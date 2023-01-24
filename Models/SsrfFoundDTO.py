from enum import Enum


class SsrfType(Enum):
    Get = 1,
    PostForm = 2,
    GetForm = 3


class SsrfFoundDTO:
    def __init__(self, ssrf_type: SsrfType, url: str, payload):
        self._url = url
        self._ssrf_type = ssrf_type
        self.payload = payload

    @property
    def url(self):
        return self._url

    @property
    def ssrf_type(self):
        return self._ssrf_type

    @property
    def payload(self):
        return self._payload



