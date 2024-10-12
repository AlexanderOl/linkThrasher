class GetRequestDTO:
    def __init__(self, *args):
        self._url = args[0]
        if len(args) == 1:
            self._response_length = 0
            self._status_code = 0
            self._content_type = '0'
        elif len(args) == 2:
            self._response_length = len(args[1].text)
            self._status_code = args[1].status_code
            if 'Content-Type' in args[1].headers:
                self._content_type = args[1].headers['Content-Type']
            else:
                self._content_type = 'No Content-Type'

    @property
    def url(self) -> str:
        return self._url

    @property
    def response_length(self) -> int:
        return self._response_length

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def content_type(self) -> str:
        return self._content_type

    def __str__(self):
        return f'{self._url} - Code:{self._status_code} - Length:{self._response_length} - Type:{self._content_type}'
