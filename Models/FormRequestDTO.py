from typing import List

from Models import GetRequestDTO


class FormDetailsDTO:
    def __init__(self, action: str, params: {}, method_type: str):
        self._key = f"{action};{';'.join(params.keys())}"
        self._action = action
        self._params = params
        self._method_type = method_type

    @property
    def key(self):
        return self._key

    @property
    def action(self):
        return self._action

    @property
    def params(self):
        return self._params

    @property
    def method_type(self):
        return self._method_type

    def __str__(self):
        return f'{{Action:{self._action},Method:{self._method_type}}}'


class FormRequestDTO:
    def __init__(self, url: str, form_params: List[FormDetailsDTO], parent_get_dto: GetRequestDTO):
        self._url = url
        self._form_params = form_params
        self._status_code = parent_get_dto.status_code
        self._response_length = parent_get_dto.response_length
        self._parent_url = parent_get_dto.url
        self._key = ';'.join([param.key for param in form_params])

    @property
    def key(self):
        return self._key

    @property
    def url(self):
        return self._url

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def response_length(self) -> int:
        return self._response_length

    @property
    def form_params(self) -> List[FormDetailsDTO]:
        return self._form_params

    @property
    def parent_url(self) -> str:
        return self._parent_url

    def __str__(self):
        details = ''
        for form in self._form_params:
            details += f"{form},"
        if details.endswith(','):
            details = details[:-1]
        return f'Link:{self._url}, FormDetails:[{details}]'
