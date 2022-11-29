import requests

from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager


class SubdomainChecker:
    def __init__(self, domain, headers, download_path):
        self.__domain = domain
        self.__tool_name = self.__class__.__name__
        self.__headers = headers
        self.__download_path = download_path
        self.__checked_subdomains = set()

    def check_subdomains(self, all_subdomains: set()) -> set():
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        checked_subdomains = cache_manager.get_saved_result()

        if not checked_subdomains:
            checked_subdomains = set()
            cookie_manager = CookieManager(self.__domain, self.__download_path)
            raw_cookies = cookie_manager.get_raw_cookies()
            cookies = cookie_manager.get_cookies_dict(raw_cookies)

            for subdomain in all_subdomains:
                url = f'http://{subdomain}/'
                try:
                    response = requests.get(url, headers=self.__headers, cookies=cookies, timeout=5)
                    print(f'{url} - status_code:{response.status_code}')
                    checked_subdomains.add(url)
                except requests.exceptions.SSLError:
                    url = url.replace('http:', 'https:')
                    try:
                        response = requests.get(url, headers=self.__headers, cookies=cookies, timeout=5)
                        print(f'{url} - status_code:{response.status_code}')
                        checked_subdomains.add(url)
                    except Exception as ex:
                        print(ex)
                except requests.exceptions.ConnectionError:
                    continue
                except Exception as ex:
                    print(ex)
            cache_manager.save_result(checked_subdomains)
        return checked_subdomains
