import os
import inject

from typing import List
from urllib.parse import urlparse, parse_qs
from Common.Logger import Logger
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper
from Models.Constants import SOCIAL_MEDIA
from Models.HeadRequestDTO import HeadRequestDTO


class Hakrawler:
    def __init__(self):
        self._max_depth = os.environ.get('max_depth')
        self._threads = f'{os.environ.get("threads")}'
        self._tool_name = self.__class__.__name__
        self._logger = inject.instance(Logger)
        self._head_dtos: List[HeadRequestDTO] = []
        self._cookie_manager = inject.instance(CookieHelper)

    def get_requests_dtos(self, start_url) -> set[str]:

        domain = urlparse(start_url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(domain, start_url)
            cache_manager.cache_result(result)

        self._logger.log_info(f'({domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self, domain: str, start_url) -> set[str]:

        raw_cookies = self._cookie_manager.get_raw_cookies(domain)

        cookie_param = ''
        if raw_cookies:
            cookie_param = f"-h 'Cookie: {raw_cookies}'"

        command = f"echo '{start_url}' | hakrawler -d {self._max_depth} {cookie_param} -t {self._threads}"
        stream = os.popen(command)
        bash_outputs = stream.readlines()
        href_urls = set()
        for output in bash_outputs:
            if output.endswith('\n'):
                output = output[:-1]
            if output.endswith('/'):
                output = output[:-1]
            if output.startswith('[href] '):
                output = output.replace('[href] ', '')
                if not any(word in output for word in SOCIAL_MEDIA) and domain in output:
                    href_urls.add(output)

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
            result_lines.add(line.rstrip())

        return result_lines


