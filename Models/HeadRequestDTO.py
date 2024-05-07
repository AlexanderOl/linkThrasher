from typing import List
from urllib.parse import urlparse
from requests.models import Response

from Common.RequestChecker import RequestChecker


class HeadRequestDTO:
    def __init__(self, response: Response):
        self._url = response.url
        self._key = RequestChecker().get_url_key(self._url)
        parsed = urlparse(self._url)
        self._query_params = list([r.split('=')[0] for r in parsed.query.split('&') if r.strip()])

        self._status_code = response.status_code
        if 'Content-Type' in response.headers:
            self._content_type = response.headers['Content-Type']
        else:
            self._content_type = 'No Content-Type'

    @property
    def query_params(self) -> List[str]:
        return self._query_params

    @property
    def key(self) -> str:
        return self._key

    @property
    def url(self) -> str:
        return self._url

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def content_type(self) -> str:
        return self._content_type

    def __str__(self):
        return f'HEAD: {self._url} - Code:{self._status_code} - Type:{self._content_type}'
