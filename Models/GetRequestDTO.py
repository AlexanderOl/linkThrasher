
class GetRequestDTO:
    def __init__(self, link, web_page):
        self._link = link
        self.web_page = web_page

    def link(self):
        return self._link

    def web_page(self):
        return self.web_page

    def __str__(self):
        return f'Link:{self._link}'

