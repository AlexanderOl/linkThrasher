
class GetRequestDTO:
    def __init__(self, link, web_page, status_code):
        self._link = link
        self._web_page = web_page
        self._response_length = len(web_page)
        self._status_code = status_code

    @property
    def link(self) -> str:
        return self._link

    @property
    def web_page(self) -> str:
        return self._web_page

    @property
    def response_length(self) -> int:
        return self._response_length

    @property
    def status_code(self) -> int:
        return self._status_code

    def __str__(self):
        return f'Link:{self.link}'

