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


class FormRequestDTO:
    def __init__(self, link: str, form_params: List[FormDetailsDTO]):
        self._link = link
        self._form_params = form_params

    @property
    def link(self):
        return self._link

    @property
    def form_params(self):
        return self._form_params

