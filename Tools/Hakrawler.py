import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import List

import inject

from Common.Logger import Logger
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Helpers.CookieHelper import CookieHelper
from Models.Constants import SOCIAL_MEDIA, URL_IGNORE_EXT_REGEX, VALID_STATUSES
from Models.HeadRequestDTO import HeadRequestDTO
from Tools.LinkFinder import LinkFinder


class Hakrawler:
    def __init__(self):
        self._max_depth = os.environ.get('max_depth')
        self._threads = f'{os.environ.get("threads")}'
        self._tool_name = self.__class__.__name__
        self._request_handler = inject.instance(RequestHandler)
        self._thread_man = inject.instance(ThreadManager)
        self._link_finder = inject.instance(LinkFinder)
        self._logger = inject.instance(Logger)
        self._head_dtos: List[HeadRequestDTO] = []
        self._checked_hrefs = set()
        self._cookie_manager = inject.instance(CookieHelper)

    def get_requests_dtos(self, start_url) -> List[HeadRequestDTO]:
        domain = urlparse(start_url).netloc
        cache_manager = CacheHelper('Hakrawler', domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(domain, start_url)
            cache_manager.cache_result(result)

        self._logger.log_info(f'({domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self, domain: str, start_url) -> list[HeadRequestDTO]:

        raw_cookies = self._cookie_manager.get_raw_cookies(domain)

        cookie_param = ''
        if raw_cookies:
            cookie_param = f"-h 'Cookie: {raw_cookies}'"

        command = f"echo '{start_url}' | hakrawler -d {self._max_depth} {cookie_param} -t {self._threads}"
        stream = os.popen(command)
        bash_outputs = stream.readlines()
        href_urls = set()
        script_urls = set()
        for output in bash_outputs:
            if output.endswith('\n'):
                output = output[:-1]
            if output.endswith('/'):
                output = output[:-1]
            if output.startswith('[href] '):
                output = output.replace('[href] ', '')
                if not any(word in output for word in SOCIAL_MEDIA) and domain in output:
                    href_urls.add(output)
            elif output.startswith('[script] '):
                output = output.replace('[script] ', '')
                if not any(word in output for word in SOCIAL_MEDIA) and domain in output:
                    script_urls.add(output)

        get_urls_from_js = self._link_finder.search_urls_in_js(script_urls, start_url)
        href_urls.update(get_urls_from_js)

        result_lines = set()
        unique_keys = {}
        for line in href_urls:
            line_domain = urlparse(line)
            key = f"{line_domain.path.rstrip('/').count('/')}{''.join(parse_qs(line_domain.query).keys())}"
            if key not in unique_keys:
                unique_keys[key] = 0
            if unique_keys[key] >= 100:
                continue
            unique_keys[key] += 1
            result_lines.add(line)

        self._thread_man.run_all(self.__check_href_urls, result_lines, debug_msg=f'{self._tool_name} ({domain})')

        return self._head_dtos

    def __check_href_urls(self, url: str):
        try:
            url_parts = urlparse(url)
            if url_parts.path in self._checked_hrefs or URL_IGNORE_EXT_REGEX.search(url):
                return
            else:
                self._checked_hrefs.add(url_parts.path)
            response = self._request_handler.send_head_request(url, timeout=5)
            if response is None:
                return

            if response.status_code in VALID_STATUSES:
                self._head_dtos.append(HeadRequestDTO(response))

            return self._head_dtos

        except Exception as inst:
            self._logger.log_error(f'[{datetime.now().strftime("%H:%M:%S")}]: Unable to parse url - {url}. '
                                   f'Hakrawler exception: {inst}')


