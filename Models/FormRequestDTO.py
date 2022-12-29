from typing import List


class FormDetailsDTO:
    def __init__(self, action: str, params: {}, method_type: str):
        self._action = action
        self._params = params
        self._method_type = str.upper(method_type)

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
    def __init__(self, url: str, form_params: List[FormDetailsDTO]):
        self._url = url
        self._form_params = form_params

    @property
    def url(self):
        return self._url

    @property
    def form_params(self) -> List[FormDetailsDTO]:
        return self._form_params

    def __str__(self):
        details = ''
        for form in self._form_params:
            details += f"{form},"
        if details.endswith(','):
            details = details[:-1]
        return f'Link:{self._url},FormDetails:[{details}]'
