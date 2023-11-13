from enum import Enum


class InjectionType(Enum):
    Sqli_Get_Error = 0,
    Sqli_Get_Time = 1,
    Sqli_Get_Bool = 2,
    Sqli_PostForm_Error = 3,
    Sqli_PostForm_Time = 4,
    Sqli_PostForm_Bool = 5,
    Ssti_Get = 6,
    Ssti_PostForm = 7,
    Xss_Get = 8,
    Xss_PostForm = 9,
    Xss_Stored = 10,
    Open_Redirect_PostForm = 11,
    Open_Redirect_Get = 12


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
        return f'Url: {self._url}, Injection: {self._inj_type}, Details: {self._header_msg.strip()}, Payload: {self._payload}'
