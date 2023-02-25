import os
import re
from http.cookies import SimpleCookie


class CookieManager:
    def __init__(self, domain: str):
        main_domain = '.'.join(domain.split('.')[-2:])
        download_path = os.environ.get('download_path')
        self.cookie_file = f"{download_path}cookies-{main_domain.replace('.','-')}.txt"

    def get_raw_cookies(self):
        result = ''
        if os.path.exists(self.cookie_file):
            cookies = {}
            with open(self.cookie_file, 'r') as fp:
                for line in fp:
                    if not re.match(r'^\#', line):
                        line_fields = line.strip().split('\t')
                        if len(line_fields) == 7:
                            cookies[line_fields[5]] = line_fields[6]
            result = "; ".join([str(x) + "=" + str(y) for x, y in cookies.items()])
        return result

    def get_cookies_dict(self, raw_cookies):
        # cookies = requests.utils.cookiejar_from_dict(json.load(f))
        cookie = SimpleCookie()
        cookie.load(raw_cookies)
        cookies = {}
        for key, morsel in cookie.items():
            cookies[key] = morsel.value
        return cookies

