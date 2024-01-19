from typing import List
from urllib.parse import urlparse
from requests.models import Response


class HeadRequestDTO:
    def __init__(self, response: Response):
        self._url = response.url
        self._key = self.__init_url_key()
        parsed = urlparse(self._url)
        self._query_params = list([r for r in parsed.query.split('&') if r.strip()])

        self._status_code = response.status_code
        if 'Content-Type' in response.headers:
            self._content_type = response.headers['Content-Type']
        else:
            self._content_type = 'No Content-Type'

    def __init_url_key(self):
        query_params = []
        parsed = urlparse(self._url)
        params = parsed.query.split('&')

        for param in params:
            split = param.split('=')
            if len(split) == 2:
                query_params.append(split[1])
        key = f'{parsed.netloc};{parsed.path};{"&".join(query_params)}'
        return key

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
