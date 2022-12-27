from typing import List

import validators
from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.RequestHandler import RequestHandler
from Managers.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO


class SubdomainChecker:
    def __init__(self, domain, headers, download_path):
        self._checked_subdomains: List[GetRequestDTO] = []
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._last_10_resp_size_attempt = {}
        cookie_manager = CookieManager(self._domain, download_path)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)
        self._request_handler = RequestHandler(cookies, headers)

    def check_all_subdomains(self, all_subdomains: set) -> List[GetRequestDTO]:
        cache_manager = CacheManager(self._tool_name, self._domain)
        checked_subdomains = cache_manager.get_saved_result()

        if not checked_subdomains:

            if len(all_subdomains) == 0:
                all_subdomains.add(f'{self._domain}')

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_subdomain, all_subdomains)

            filtered_dtos: List[GetRequestDTO] = []
            for item in self._checked_subdomains:
                curr_resp_length = item.response_length
                curr_status_code = item.status_code
                if len(filtered_dtos) == 0 or \
                        len(list(filter(lambda dto: dto.response_length == curr_resp_length and
                                               dto.status_code == curr_status_code, filtered_dtos))) < 3:
                    filtered_dtos.append(item)

            cache_manager.save_result(filtered_dtos)
            return filtered_dtos
        else:
            return checked_subdomains

    def __check_subdomain(self, subdomain):
        url = f'http://{subdomain}/'
        self._request_handler.handle_request(url=url,
                                             except_ssl_action=self.__except_ssl_action,
                                             except_ssl_action_args=[url])

    def __except_ssl_action(self, args):
        url = args[0]
        url = url.replace('http:', 'https:')
        if validators.url(url):
            response = self._request_handler.handle_request(url)
            if response is not None:
                print(f'{url} - status_code:{response.status_code}', flush=True)
                self._checked_subdomains.append(GetRequestDTO(url, response))
