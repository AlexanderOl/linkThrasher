import os
from typing import List

import validators
from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.RequestHandler import RequestHandler
from Managers.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO


class SubdomainChecker:
    def __init__(self, domain, headers):
        self._checked_subdomains: List[GetRequestDTO] = []
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._last_10_resp_size_attempt = {}
        cookie_manager = CookieManager(domain)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)
        self._request_handler = RequestHandler(cookies, headers)
        self._out_of_scope_domains = os.environ.get("out_of_scope_domains")

    def check_all_subdomains(self, all_subdomains: set) -> List[GetRequestDTO]:
        cache_manager = CacheManager(self._tool_name, self._domain)
        checked_subdomains = cache_manager.get_saved_result()
        out_of_scope = [x for x in self._out_of_scope_domains.split(';') if x]
        if not checked_subdomains:

            subdomains = set(
                [subdomain for subdomain in all_subdomains if all(oos not in subdomain for oos in out_of_scope)])

            if len(subdomains) == 0:
                subdomains.add(f'{self._domain}')

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_subdomain, subdomains, debug_msg=self._tool_name)

            if len(self._checked_subdomains) > 2:
                origin = next((s for s in self._checked_subdomains if f'/{self._domain}/' in s.url), None)
                www = next((s for s in self._checked_subdomains if f'/www.{self._domain}/' in s.url), None)
                if origin is not None and www is not None and \
                        origin.status_code == www.status_code and \
                        origin.response_length == www.response_length:
                    self._checked_subdomains.remove(www)

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
            filtered_subdomains = [dto for dto in checked_subdomains if all(oos not in dto.url for oos in out_of_scope)]
            return filtered_subdomains

    def __check_subdomain(self, subdomain):
        url = f'https://{subdomain}/'
        response = self._request_handler.handle_request(url=url,
                                                        except_ssl_action=self.__except_ssl_action,
                                                        except_ssl_action_args=[url],
                                                        timeout=5)

        if response is not None:
            self._checked_subdomains.append(GetRequestDTO(url, response))

    def __except_ssl_action(self, args):
        url = args[0]
        url = url.replace('https:', 'http:')
        if validators.url(url):
            response = self._request_handler.handle_request(url, timeout=5)
            if response is not None:
                self._checked_subdomains.append(GetRequestDTO(url, response))
