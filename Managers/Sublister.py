import os
import requests

from datetime import datetime

from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager


class Sublister:
    def __init__(self, domain, headers, download_path):
        self._domain = domain
        self._headers = headers
        self._download_path = download_path
        self.__checked_redirect_url_parts = {}

    def get_subdomains(self) -> set:
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SubdomainManager started...')
        cache_manager = CacheManager('SubdomainManager', self._domain)
        result = cache_manager.get_saved_result()
        if not result:
            subdomains = set()
            command = f'cd /root/Desktop/TOOLs/Sublist3r/; python sublist3r.py -d {self._domain} | grep "Total Unique Subdomains Found" -A 999'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            skip_first_line = True
            for line in bash_outputs:
                if skip_first_line:
                    skip_first_line = False
                    continue
                subdomains.add(line.replace('\x1b[92m', '').replace('\x1b[0m\n', ''))
            result = self.__check_subdomains(subdomains)
            cache_manager.save_result(result)
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SubdomainManager found {len(result)} items')
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
                response = requests.get(url, headers=self._headers, cookies=cookies, timeout=5)
                if response.status_code == 200:
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
            except Exception as ex:
                print(ex)
        return checked_subdomains
