import os
import re
from http.cookies import SimpleCookie


class CookieHelper:
    def __init__(self, domain: str):
        main_domain = '.'.join(domain.split('.')[-2:])
        download_path = os.environ.get('download_path')
        self._domain_cookie_file = f"{download_path}cookies-{main_domain.replace('.', '-')}.txt"
        self._cookie_file = f"{download_path}cookies.txt"

    def get_raw_file(self):
        found_cookie_file = ''
        if os.path.exists(self._domain_cookie_file):
            found_cookie_file = self._domain_cookie_file
        elif os.path.exists(self._cookie_file):
            found_cookie_file = self._cookie_file
        return found_cookie_file

    def get_raw_cookies(self):
        result = ''

        found_cookie_file = ''
        if os.path.exists(self._domain_cookie_file):
            found_cookie_file = self._domain_cookie_file
        elif os.path.exists(self._cookie_file):
            found_cookie_file = self._cookie_file

        if found_cookie_file:
            cookies = {}
            with open(found_cookie_file, 'r') as fp:
                for line in fp:
                    if not re.match(r'^\#', line):
                        line_fields = line.strip().split('\t')
                        if len(line_fields) == 7:
                            cookies[line_fields[5]] = line_fields[6]
            result = "; ".join([str(x) + "=" + str(y) for x, y in cookies.items()])
        return result

    @staticmethod
    def get_cookies_dict(raw_cookies):
        # cookies = requests.utils.cookiejar_from_dict(json.load(f))
        cookie = SimpleCookie()
        cookie.load(raw_cookies)
        cookies = {}
        for key, morsel in cookie.items():
            cookies[key] = morsel.value
        return cookies
