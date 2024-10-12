import os
import re
from http.cookies import SimpleCookie


class CookieHelper:
    def __init__(self):
        self._download_path = os.environ.get('download_path')
        self._cookie_file = f"{self._download_path}cookies.txt"
        self._domain_cookie_file = None

    def get_raw_file(self, domain: str):

        domain_cookie_file = self.__get_domain_cookie_file(domain)
        found_cookie_file = ''
        if os.path.exists(domain_cookie_file):
            found_cookie_file = domain_cookie_file
        elif os.path.exists(self._cookie_file):
            found_cookie_file = self._cookie_file
        return found_cookie_file

    def get_raw_cookies(self, domain):
        result = ''
        found_cookie_file = ''
        domain_cookie_file = self.__get_domain_cookie_file(domain)
        if os.path.exists(domain_cookie_file):
            found_cookie_file = domain_cookie_file
        elif os.path.exists(self._cookie_file):
            found_cookie_file = self._cookie_file

        if found_cookie_file:
            cookies = {}
            with open(found_cookie_file, 'r', encoding='utf-8', errors='ignore') as fp:
                for line in fp:
                    if not re.match(r'^\#', line):
                        line_fields = line.strip().split('\t')
                        if len(line_fields) == 7:
                            cookies[line_fields[5]] = line_fields[6]
            result = "; ".join([str(x) + "=" + str(y) for x, y in cookies.items()])
        return result

    def get_cookies_dict(self, domain: str):
        raw_cookies = self.get_raw_cookies(domain)

        cookie = SimpleCookie()
        cookie.load(raw_cookies)
        cookies = {}
        for key, morsel in cookie.items():
            cookies[key] = morsel.value
        return cookies

    def __get_domain_cookie_file(self, domain) -> str:
        if self._domain_cookie_file is None:
            main_domain = '.'.join(domain.split('.')[-2:])
            self._domain_cookie_file = f"{self._download_path}cookies-{main_domain.replace('.', '-')}.txt"
        return self._domain_cookie_file
