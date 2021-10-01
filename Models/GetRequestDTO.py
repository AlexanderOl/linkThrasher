import json


class GetRequestDTO:
    def __init__(self, link, web_page):
        self.link = link
        self.web_page = web_page

    def link(self):
        return self.link

    def web_page(self):
        return self.web_page


