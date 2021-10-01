import json
from enum import Enum


class XssType(Enum):
    Get = 1,
    PostForm = 2,
    GetForm = 3


class XssFoundDTO:
    def __init__(self, xss_type: XssType, url: str, payload, web_page):
        self.url = url
        self.xss_type = xss_type
        self.payload = payload
        self.web_page = web_page

    def url(self):
        return self.url

    def xss_type(self):
        return self.xss_type

    def payload(self):
        return self.payload

    def web_page(self):
        return self.web_page


