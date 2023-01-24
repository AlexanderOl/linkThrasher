from enum import Enum


class InjectionType(Enum):
    Sqli_ERROR = 0,
    Sqli_TIME = 1,
    Sqli_FORM_ERROR = 2,
    Sqli_FORM_GET_ERROR = 3,
    Ssti_Get = 4,
    Ssti_PostForm =5,
    Ssti_GetForm = 6,
    Xss_Get = 7,
    Xss_PostForm = 8,
    Xss_GetForm = 9,
    Open_Redirect_POST = 10,
    Open_Redirect_GET = 11


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
        return f'url: {self._url}, sqliType: {self._inj_type}, details: {self._header_msg}'
