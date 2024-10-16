import os
import inject

from datetime import datetime
from typing import List
from urllib.parse import urlparse
from Common.RequestChecker import RequestChecker
from Helpers.CacheHelper import CacheHelper
from Models.Constants import URL_IGNORE_EXT_REGEX
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Waybackurls:

    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._result: List[HeadRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._checked_hrefs = set()
        self._out_of_scope = os.environ.get("out_of_scope")
        self._wayback_max_size = 50000
        self._request_checker = inject.instance(RequestChecker)

    def get_requests_dtos(self, start_url) -> set[str]:

        domain = urlparse(start_url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        result = cache_manager.get_saved_result()
        if result is None:

            out_of_scope = [x for x in self._out_of_scope.split(';') if x]
            if any(oos in domain for oos in out_of_scope):
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) out of scope waybackurls')
                return set()
            result = self.__get_urls(domain)
            cache_manager.cache_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self, domain: str) -> set[str]:
        res_file = f'{self._tool_result_dir}/{domain.replace(":", "_")}.txt'

        command = f"echo '{domain}' | waybackurls > {res_file}"
        stream = os.popen(command)
        stream.read()

        href_urls = set()
        text_file = open(res_file, 'r', encoding='utf-8', errors='ignore')
        lines = text_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if domain in netloc:
                href_urls.add(line.rstrip())
        text_file.close()

        urls = self.__filter_urls(href_urls)

        return urls

    def __filter_urls(self, href_urls) -> set[str]:
        urls = set()
        checked_key = set()

        for href_url in href_urls:
            parsed_parts = urlparse(href_url)
            if URL_IGNORE_EXT_REGEX.search(parsed_parts.path):
                continue

            key = self._request_checker.get_url_key(href_url)
            if key in checked_key:
                continue
            checked_key.add(key)
            urls.add(href_url)

        if len(urls) > self._wayback_max_size:
            urls_with_params = set([url for url in urls if '?' in urls])
            return urls_with_params
        else:
            return urls
