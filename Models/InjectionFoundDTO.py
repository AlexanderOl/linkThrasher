from enum import Enum


class InjectionType(Enum):
    Sqli_Get_Error = 0,
    Sqli_Get_Time = 1,
    Sqli_PostForm_Error = 2,
    Ssti_Get = 3,
    Ssti_PostForm = 4,
    Xss_Get = 5,
    Xss_PostForm = 6,
    Open_Redirect_PostForm = 7,
    Open_Redirect_Get = 8


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

    def __str__(self):
        return f'Url: {self._url}, Injection: {self._inj_type}, Details: {self._header_msg}'