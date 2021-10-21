import os
import re
from http.cookies import SimpleCookie

class CookieManager:
    def __init__(self, domain, download_path):
        self.domain = domain
        self.download_path = download_path

    def get_raw_cookies(self):
        cookie_file = f'{self.download_path}\\{self.domain}_cookies.txt'
        result = ''
        if os.path.exists(cookie_file):
            cookies_dict = self.__parse_cookie_file(cookie_file)
            result = "; ".join([str(x) + "=" + str(y) for x, y in cookies_dict.items()])
        return result

    def __parse_cookie_file(self, cookie_file):
        cookies = {}
        with open(cookie_file, 'r') as fp:
            for line in fp:
                if not re.match(r'^\#', line):
                    line_fields = line.strip().split('\t')
                    if len(line_fields) == 7:
                        cookies[line_fields[5]] = line_fields[6]
        return cookies

    def get_cookies_dict(self, raw_cookie):
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        cookies = {}
        for key, morsel in cookie.items():
            cookies[key] = morsel.value
        return cookies

test_domain = 'dell.com'
test_download_path = "C:\\Users\\oleksandr oliinyk\\Downloads"

def test():
    cm = CookieManager(test_domain, test_download_path)
    print(cm.get_raw_cookies())

test()
