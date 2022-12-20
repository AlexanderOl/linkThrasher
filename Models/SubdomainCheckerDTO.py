class SubdomainCheckerDTO:
    def __init__(self, url, status_code):
        self._url = url
        self._status_code = status_code

    @property
    def url(self) -> str:
        return self._url

    @property
    def status_code(self) -> int:
        return self._status_code

    def __str__(self):
        return f'StatusCode: {self._status_code}, Url - {self._url}'
