import os
import socket
import subprocess
from datetime import datetime
from typing import List
from urllib.parse import urlparse

import validators

from Common.CollectionUtil import CollectionUtil
from Common.ProcessKiller import ProcessKiller
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.HeadRequestDTO import HeadRequestDTO


class SubdomainChecker:
    def __init__(self, domain, headers):
        self._checked_subdomains: List[HeadRequestDTO] = []
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._last_10_resp_size_attempt = {}
        cookie_manager = CookieHelper(domain)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)
        self._request_handler = RequestHandler(cookies, headers)
        self._out_of_scope_domains = os.environ.get("out_of_scope_domains")
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._checked_ips = set()
        self._chunk_size = 100

    def check_all_subdomains(self, all_subdomains: set) -> List[HeadRequestDTO]:
        cache_manager = CacheHelper(self._tool_name, self._domain)
        checked_subdomains = cache_manager.get_saved_result()
        out_of_scope = [x for x in self._out_of_scope_domains.split(';') if x]
        if not checked_subdomains and not isinstance(checked_subdomains, List):

            subdomains = set(
                [subdomain for subdomain in all_subdomains if all(oos not in subdomain for oos in out_of_scope)])

            ips = self.__get_ips(subdomains)
            subdomains.update(ips)

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_subdomain, subdomains, debug_msg=self._tool_name)

            if len(self._checked_subdomains) > 2:
                origin = next((s for s in self._checked_subdomains if f'/{self._domain}/' in s.url), None)
                www = next((s for s in self._checked_subdomains if f'/www.{self._domain}/' in s.url), None)
                if origin is not None and www is not None and \
                        origin.status_code == www.status_code:
                    self._checked_subdomains.remove(www)

            filtered_dtos: List[HeadRequestDTO] = []
            for item in self._checked_subdomains:
                curr_status_code = item.status_code

                if len(filtered_dtos) == 0 or \
                        len(list(filter(lambda dto: dto.status_code == curr_status_code, filtered_dtos))) < 10:
                    filtered_dtos.append(item)

            cache_manager.save_result(filtered_dtos)
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
        except socket.gaierror:
            return

        url = f'https://{subdomain}'
        response = self._request_handler.send_head_request(url=url,
                                                           except_ssl_action=self.__except_ssl_action,
                                                           except_ssl_action_args=[url],
                                                           timeout=5)

        if response is not None:
            if 'Server' in response.headers and response.headers['Server'] == 'cloudflare':
                return
            elif (len(response.history) > 0 and str(response.history[0].status_code).startswith('3') and
                  'Location' in response.history[0].headers):
                redirect = response.history[0].headers['Location']
                self.__check_redirect_urls(url, redirect)

            elif str(response.status_code).startswith('3') and 'Location' in response.headers:
                redirect = response.headers['Location']
                self.__check_redirect_urls(url, redirect)
            elif all(dto.url != url for dto in self._checked_subdomains):
                self._checked_subdomains.append(HeadRequestDTO(response))
            else:
                print(f'({url}) url already added')

    def __except_ssl_action(self, args):
        url = args[0]
        url = url.replace('https:', 'http:')
        if validators.url(url):
            response = self._request_handler.send_head_request(url, timeout=5)
            if response is not None:
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
        if response2 is not None and all(dto.url != redirect_url for dto in self._checked_subdomains):
            self._checked_subdomains.append(HeadRequestDTO(response2))

    def __get_ips(self, subdomains) -> set:
        if not os.path.exists(f'{self._tool_result_dir}/{self._domain}'):
            os.makedirs(f'{self._tool_result_dir}/{self._domain}')

        subs_file = f'{self._tool_result_dir}/{self._domain}/subs.txt'
        json_file = open(subs_file, 'w')
        for subdomain in subdomains:
            json_file.write(f"{subdomain}\n")
        json_file.close()

        cmd_arr = ['dnsx', '-l', subs_file, '-silent', '-a', '-resp-only']
        pk = ProcessKiller()
        bash_outputs = pk.run_temp_process(cmd_arr, self._domain, timeout=1200)

        ips = set()

        for output in bash_outputs:
            ips.add(output)

        if os.path.exists(subs_file):
            os.remove(subs_file)

        return ips
