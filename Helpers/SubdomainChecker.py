import os
import socket
import inject
import validators

from typing import List
from urllib.parse import urlparse
from Common.Logger import Logger
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.HeadRequestDTO import HeadRequestDTO


class SubdomainChecker:
    def __init__(self):
        self._checked_subdomains: List[HeadRequestDTO] = []
        self._tool_name = self.__class__.__name__
        self._last_10_resp_size_attempt = {}
        self._out_of_scope = os.environ.get("out_of_scope")
        self._chunk_size = 100
        self._checked_ips = set()
        self._logger = inject.instance(Logger)
        self._request_handler = inject.instance(RequestHandler)
        self._thread_manager = inject.instance(ThreadManager)

    def check_all_subdomains(self, domain: str, all_subdomains: set, avoid_cache=False) -> List[HeadRequestDTO]:
        self._domain = domain
        cache_manager = CacheHelper(self._tool_name, domain)
        checked_subdomains = cache_manager.get_saved_result()
        out_of_scope = [x for x in self._out_of_scope.split(';') if x]
        if (not checked_subdomains and not isinstance(checked_subdomains, List)) or avoid_cache:

            subdomains = set(
                [subdomain.rstrip('.') for subdomain in all_subdomains
                 if all(oos not in subdomain for oos in out_of_scope)])

            self._thread_manager.run_all(self.__check_subdomain, subdomains, debug_msg=f'{self._tool_name} ({domain})')

            if len(self._checked_subdomains) > 2:
                origin = next((s for s in self._checked_subdomains if f'/{domain}/' in s.url), None)
                www = next((s for s in self._checked_subdomains if f'/www.{domain}/' in s.url), None)
                if origin is not None and www is not None and \
                        origin.status_code == www.status_code:
                    self._checked_subdomains.remove(www)

            filtered_dtos: List[HeadRequestDTO] = []
            for item in self._checked_subdomains:
                curr_status_code = item.status_code

                if len(filtered_dtos) == 0 or \
                        len(list(filter(lambda dto: dto.status_code == curr_status_code, filtered_dtos))) < 10:
                    filtered_dtos.append(item)

            cache_manager.cache_result(filtered_dtos)
            return filtered_dtos
        else:
            filtered_subdomains = [dto for dto in checked_subdomains if all(oos not in dto.url for oos in out_of_scope)]
            return filtered_subdomains

    def __check_subdomain(self, subdomain):
        try:
            ip = socket.gethostbyname(subdomain)
            if ip not in self._checked_ips:
                self._checked_ips.add(ip)
            else:
                return
        except Exception as inst:
            self._logger.log_error(f'Domain ({subdomain} - check_subdomain) - Exception: {inst}')

        url = f'https://{subdomain}'
        response = self._request_handler.send_head_request(url=url,
                                                           except_ssl_action=self.__except_ssl_action,
                                                           except_ssl_action_args=[url],
                                                           timeout=3)

        if response is not None:
            if (len(response.history) > 0
                    and str(response.history[0].status_code).startswith('3')
                    and 'Location' in response.history[0].headers):
                redirect = response.history[0].headers['Location']
                self.__check_redirect_urls(url, redirect)

            elif str(response.status_code).startswith('3') and 'Location' in response.headers:
                redirect = response.headers['Location']
                self.__check_redirect_urls(url, redirect)
            elif all(urlparse(dto.url).netloc.replace('www.', '') !=
                     urlparse(url).netloc.replace('www.', '')
                     for dto in self._checked_subdomains):
                self._checked_subdomains.append(HeadRequestDTO(response))
            else:
                self._logger.log_info(f'({url}) url already added')

    def __except_ssl_action(self, args):
        url = args[0]
        url = url.replace('https:', 'http:')
        if validators.url(url):
            response = self._request_handler.send_head_request(url, timeout=5)
            if response is not None and (len(response.history) > 0
                                         and str(response.history[0].status_code).startswith('3')
                                         and 'Location' in response.history[0].headers):
                redirect = response.history[0].headers['Location']
                self.__check_redirect_urls(url, redirect)
            elif response is not None:
                self._checked_subdomains.append(HeadRequestDTO(response))

    def __check_redirect_urls(self, base_url, redirect):
        parsed = urlparse(redirect)
        if redirect and redirect[0] == '/':
            redirect_url = f"{base_url}{redirect}"
        elif not parsed or self._domain not in parsed.netloc:
            return
        else:
            redirect_url = redirect
        response2 = self._request_handler.send_head_request(url=redirect_url,
                                                            except_ssl_action=self.__except_ssl_action,
                                                            except_ssl_action_args=[base_url],
                                                            timeout=5)
        if not response2:
            return

        if str(response2.status_code).startswith('3') and 'Location' in response2.headers:
            redirect2 = response2.headers['Location']
            self.__check_redirect_urls(base_url, redirect2)
        elif (self._domain in urlparse(response2.url).netloc and
              all(urlparse(dto.url).netloc.replace('www.', '') !=
                  urlparse(response2.url).netloc.replace('www.', '') for dto in self._checked_subdomains)):
            self._checked_subdomains.append(HeadRequestDTO(response2))
