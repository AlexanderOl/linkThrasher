from typing import List

import requests
import validators
from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO


class SubdomainChecker:
    def __init__(self, domain, headers, download_path):
        self.__checked_subdomains: List[GetRequestDTO] = []
        self.__domain = domain
        self.__tool_name = self.__class__.__name__
        self.__headers = headers
        self.__download_path = download_path
        self.__last_10_resp_size_attempt = {}
        cookie_manager = CookieManager(self.__domain, self.__download_path)
        raw_cookies = cookie_manager.get_raw_cookies()
        self.__cookies = cookie_manager.get_cookies_dict(raw_cookies)

    def check_all_subdomains(self, all_subdomains: set) -> List[GetRequestDTO]:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        checked_subdomains = cache_manager.get_saved_result()

        if not checked_subdomains:

            if len(all_subdomains) == 0:
                all_subdomains.add(f'{self.__domain}')

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_subdomain, all_subdomains)

            filtered_dtos: List[GetRequestDTO] = []
            for item in self.__checked_subdomains:
                curr_resp_length = item.response_length
                curr_status_code = item.status_code
                if len(filter(lambda dto: dto.response_length == curr_resp_length and
                                          dto.status_code == curr_status_code, filtered_dtos)) <= 10:
                    filtered_dtos.append(item)

            cache_manager.save_result(filtered_dtos)
            return filtered_dtos
        else:
            return checked_subdomains

    def __check_subdomain(self, subdomain):
        url = f'http://{subdomain}/'
        try:
            self.__send_request(url)
        except requests.exceptions.SSLError:
            url = url.replace('http:', 'https:')
            try:
                self.__send_request(url)
            except Exception as ex:
                print(ex)
        except requests.exceptions.ConnectionError:
            return
        except Exception as ex:
            print(f'Exception - {ex} on url - {url}')

    def __send_request(self, url):
        if validators.url(url):
            response = requests.get(url, headers=self.__headers, cookies=self.__cookies, timeout=5)
            print(f'{url} - status_code:{response.status_code}', flush=True)
            self.__checked_subdomains.append(GetRequestDTO(url, response))
