import os
import re
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.Constants import VALID_STATUSES, URL_IGNORE_EXT_REGEX
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Katana:
    def __init__(self, domain, raw_cookies, request_handler: RequestHandler):
        self._domain = domain
        self._raw_cookies = raw_cookies
        self._tool_name = self.__class__.__name__
        self._request_handler = request_handler
        self._result: List[HeadRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._checked_hrefs = set()
        self._max_depth = int(os.environ.get('max_depth'))

    def get_requests_dtos(self, start_url) -> List[HeadRequestDTO]:
        cache_manager = CacheHelper(self._tool_name, self._domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(start_url)
            cache_manager.cache_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self, start_url) -> List[HeadRequestDTO]:

        cookie_param = ''
        if self._raw_cookies:
            cookie_param = f"-H 'Cookie: {self._raw_cookies}'"

        res_file = f'{self._tool_result_dir}/{self._domain.replace(":", "_")}.txt'

        command = f"echo '{start_url}' | katana --timeout 3 -d {self._max_depth} -o {res_file} -jc -mrs 10000000 -kf all {cookie_param}"
        stream = os.popen(command)
        stream.read()

        href_urls = set()
        json_file = open(res_file, 'r')
        lines = json_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if self._domain in netloc:
                href_urls.add(line)
        json_file.close()

        tm = ThreadManager()
        tm.run_all(self.__check_href_urls, href_urls, debug_msg=f'{self._tool_name} ({self._domain})')

        return self._result

    def __check_href_urls(self, url: str):
        url_parts = urlparse(url)
        if url_parts.path in self._checked_hrefs or URL_IGNORE_EXT_REGEX.search(url):
            return
        else:
            self._checked_hrefs.add(url_parts.path)
        check = self._request_handler.send_head_request(url)
        if check is None:
            return
        response = self._request_handler.handle_request(url, timeout=5)
        if response is None:
            return

        if len(self._get_dtos) > 0 and any(dto for dto in self._get_dtos if
                                           dto.response_length == len(response.text) and
                                           dto.status_code == response.status_code):
            return

        if response.status_code in VALID_STATUSES:
            self._get_dtos.append(GetRequestDTO(url, response))
            self._result.append(HeadRequestDTO(response))

