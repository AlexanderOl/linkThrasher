import os
import re
import tldextract
from http.cookies import SimpleCookie


def parse_cookie_file(cookie_file):
    cookies = {}
    with open(cookie_file, 'r') as fp:
        for line in fp:
            if not re.match(r'^\#', line):
                lineFields = line.strip().split('\t')
                if len(lineFields) == 7:
                    cookies[lineFields[5]] = lineFields[6]
    return cookies




class CookieManager:
    def __init__(self, domain):
        self.domain = domain

    def get_raw_cookies(self):
        cookie_file = f'/root/Downloads/{self.domain}_cookies.txt'
        result = ''
        if os.path.exists(cookie_file):
            cookies_dict = parse_cookie_file(cookie_file)
            result = "; ".join([str(x) + "=" + str(y) for x, y in cookies_dict.items()])
        return result

    def get_cookies_dict(self, raw_cookie):
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        cookies = {}
        for key, morsel in cookie.items():
            cookies[key] = morsel.value
        return cookies

