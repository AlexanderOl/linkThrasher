from enum import Enum


class InjectionType(Enum):
    Sqli_Get_Error = 0,
    Sqli_Get_Time = 1,
    Sqli_PostForm_Error = 2,
    Sqli_PostForm_Time = 3,
    Ssti_Get = 4,
    Ssti_PostForm = 5,
    Xss_Get = 6,
    Xss_PostForm = 7,
    Open_Redirect_PostForm = 8,
    Open_Redirect_Get = 9


class InjectionFoundDTO:
    def __init__(self, inj_type: InjectionType, url: str, payload: str, web_page: str, header_msg: str):
        self._url = url
        self._inj_type = inj_type
        self._payload = payload
        self._web_page = web_page
        self._response_length = len(web_page)
        self._header_msg = header_msg

    @property
    def url(self):
        return self._url

    @property
    def inj_type(self):
        return self._inj_type

    @property
    def response_length(self):
        return self._response_length

    @property
    def details_msg(self):
        return self._header_msg

    def __str__(self):
        return f'Url: {self._url}, Injection: {self._inj_type}, Details: {self._header_msg}'
