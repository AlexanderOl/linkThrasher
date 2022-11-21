import requests

from Managers.CookieManager import CookieManager


class SubdomainChecker:
    def __init__(self, domain, headers, download_path):
        self.domain = domain
        self.__headers = headers
        self.__download_path = download_path
        self.__checked_redirect_url_parts = set()
        self.__checked_subdomains = set()

    def check_subdomains(self, all_subdomains: set()) -> set():

        cookie_manager = CookieManager(self.domain, self.__download_path)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)

        for subdomain in all_subdomains:
            url = f'http://{subdomain}/'
            try:
                self.__send_request(url, cookies)
            except requests.exceptions.SSLError:
                if url.startswith('https:'):
                    return
                url = url.replace('http:', 'https:')
                try:
                    self.__send_request(url, cookies)
                except Exception as ex:
                    print(ex)
            except Exception as ex:
                print(ex)
        return self.__checked_subdomains

    def __send_request(self, url, cookies):
        response = requests.get(url, headers=self.__headers, cookies=cookies, timeout=5)
        if response.status_code < 400:
            without_url = response.url.replace(url, '')
            if without_url not in self.__checked_redirect_url_parts:
                self.__checked_redirect_url_parts.add(without_url)
                self.__checked_subdomains.add(url)
        elif 400 <= response.status_code < 500:
            print(f'{url} - status_code:{response.status_code}')
        else:
            print(f'{url} - MIGHT BE INTERESTING:{response.status_code}')
