from enum import Enum


class SstiType(Enum):
    Get = 1,
    PostForm = 2,
    GetForm = 3


class SstiFoundDTO:
    def __init__(self, url: str, ssti_type: SstiType, payload, web_page):
        self.url = url
        self.ssti_type = ssti_type
        self.payload = payload
        self.web_page = web_page

    def url(self):
        return self.url

    def ssti_type(self):
        return self.ssti_type

    def web_page(self):
        return self.web_page
