from typing import List

import requests
import validators
from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.ThreadManager import ThreadManager
from Models.SubdomainCheckerDTO import SubdomainCheckerDTO


class SubdomainChecker:
    def __init__(self, domain, headers, download_path):
        self.__checked_subdomains: List[SubdomainCheckerDTO] = []
        self.__domain = domain
        self.__tool_name = self.__class__.__name__
        self.__headers = headers
        self.__download_path = download_path

    def check_all_subdomains(self, all_subdomains: set()) -> List[SubdomainCheckerDTO]:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        checked_subdomains = cache_manager.get_saved_result()

        if not checked_subdomains:

            if len(all_subdomains) == 0:
                all_subdomains.add(f'{self.__domain}')

            cookie_manager = CookieManager(self.__domain, self.__download_path)
            raw_cookies = cookie_manager.get_raw_cookies()
            self.__cookies = cookie_manager.get_cookies_dict(raw_cookies)

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_subdomain, all_subdomains)

            cache_manager.save_result(self.__checked_subdomains)
        else:
            self.__checked_subdomains = checked_subdomains
        return self.__checked_subdomains

    def __check_subdomain(self, subdomain):
        url = f'http://{subdomain}/'
        try:
            if validators.url(url):
                response = requests.get(url, headers=self.__headers, cookies=self.__cookies, timeout=5)
                print(f'{url} - status_code:{response.status_code}', flush=True)
                self.__checked_subdomains.append(SubdomainCheckerDTO(url, response.status_code))
        except requests.exceptions.SSLError:
            url = url.replace('http:', 'https:')
            try:
                response = requests.get(url, headers=self.__headers, cookies=self.__cookies, timeout=5)
                print(f'{url} - status_code:{response.status_code}', flush=True)
                self.__checked_subdomains.append(SubdomainCheckerDTO(url, response.status_code))
            except Exception as ex:
                print(ex)
        except requests.exceptions.ConnectionError:
            return
        except Exception as ex:
            print(f'Exception - {ex} on url - {url}')
