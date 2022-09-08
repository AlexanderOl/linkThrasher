import os
import urllib

import requests

from datetime import datetime

from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager


class SubBrute:
    def __init__(self, domain):
        self.domain = domain
        self.tools_path = os.environ.get('tools_path')
        self.app_result_path = os.environ.get('app_result_path')
        self.sub_brute = 'SubBrute'
        self.__checked_redirect_url_parts = {}

    def get_subdomains(self) -> set:
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SubBrute started...')
        cache_manager = CacheManager(self.sub_brute, self.domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains:
            subdomains = set()
            command = f'cd {self.tools_path}/subbrute; python subbrute.py {self.domain}'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if self.domain in line:
                    subdomains.add(line.replace('\x1b[92m', '').replace('\n', ''))
            cache_manager.save_result(subdomains)
        result = self.__check_subdomains(subdomains)
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SubBrute found {len(result)} items')
        return result

    def __check_subdomains(self, all_subdomains: set()) -> set():
        checked_subdomains = set()
        self.__checked_redirect_url_parts = set()

        cookie_manager = CookieManager(self._domain, self._download_path)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)

        for subdomain in all_subdomains:
            url = f'http://{subdomain}/'
            try:
                response = requests.get(url, headers=self.headers, cookies=cookies, timeout=5)
                if response.status_code < 300:
                    without_url = response.url.replace(url, '')
                    if without_url not in self.__checked_redirect_url_parts:
                        self.__checked_redirect_url_parts.add(without_url)
                        checked_subdomains.add(url)
                elif 300 <= response.status_code < 400:
                    s = 1
                elif 400 <= response.status_code < 500:
                    print(f'{url} - status_code:{response.status_code}')
                else:
                    print(f'{url} - MIGHT BE INTERESTING:{response.status_code}')
            except requests.exceptions.SSLError:
                url = url.replace('http', 'https')
                response = requests.get(url, headers=self.headers, cookies=cookies, timeout=5, verify=False)
                if response.status_code == 200:
                    without_url = response.url.replace(url, '')
                    if without_url not in self.__checked_redirect_url_parts:
                        self.__checked_redirect_url_parts.add(without_url)
                        checked_subdomains.add(url)
            except Exception as ex:
                print(ex)
        return checked_subdomains
