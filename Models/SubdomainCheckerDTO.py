class SubdomainCheckerDTO:
    def __init__(self, link, status_code):
        self._link = link
        self._status_code = status_code

    @property
    def link(self) -> str:
        return self._link

    @property
    def status_code(self) -> int:
        return self._status_code

    def __str__(self):
        return f'StatusCode: {self._status_code}, Url - {self._link}'
