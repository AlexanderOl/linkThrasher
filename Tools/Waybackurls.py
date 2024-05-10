import os
import re
import uuid
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Waybackurls:
    def __init__(self, domain, raw_cookies, headers, cookies):
        self._domain = domain
        self._raw_cookies = raw_cookies
        self._social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "intercom", "atlassian"]
        self._tool_name = self.__class__.__name__
        self._request_handler = RequestHandler(cookies, headers)
        self._url_ignore_ext_regex = re.compile(
            '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
            '|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.mp4$|\.avi$|\.mp3$|\.webp$',
            re.IGNORECASE)
        self._result: List[HeadRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._checked_hrefs = set()
        self._waybackurls_out_of_scope_domains = os.environ.get("waybackurls_out_of_scope_domains")
        self._wayback_max_size = 50000
        self._request_checker = RequestChecker()

    def get_requests_dtos(self) -> List[HeadRequestDTO]:
        cache_manager = CacheHelper(self._tool_name, self._domain)
        result = cache_manager.get_saved_result()
        if result is None:

            out_of_scope = [x for x in self._waybackurls_out_of_scope_domains.split(';') if x]
            if any(oos in self._domain for oos in out_of_scope):
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) out of scope waybackurls')
                return []
            result = self.__get_urls()
            cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self) -> List[HeadRequestDTO]:
        res_file = f'{self._tool_result_dir}/{self._domain.replace(":", "_")}.txt'

        command = f"echo '{self._domain}' | waybackurls > {res_file}"
        stream = os.popen(command)
        stream.read()

        href_urls = set()
        text_file = open(res_file, 'r')
        lines = text_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if self._domain in netloc:
                href_urls.add(line)
        text_file.close()

        urls = self.__filter_urls(href_urls)

        tm = ThreadManager()
        tm.run_all(self.__check_href_urls, urls, debug_msg=f'{self._tool_name} ({self._domain})')

        return self._result

    def __check_href_urls(self, url: str):
        url_parts = urlparse(url)
        if url_parts.path in self._checked_hrefs or self._url_ignore_ext_regex.search(url):
            return
        else:
            self._checked_hrefs.add(url_parts.path)

        check = self._request_handler.send_head_request(url)
        if check is None:
            return

        response = self._request_handler.handle_request(url, timeout=3)
        if response is None:
            return

        if len(self._get_dtos) > 0 and any(dto for dto in self._get_dtos if
                                           dto.response_length == len(response.text) and
                                           dto.status_code == response.status_code):
            return

        if response.status_code < 400 or response.status_code == 500:
            self._get_dtos.append(GetRequestDTO(url, response))
            self._result.append(HeadRequestDTO(response))

    def __filter_urls(self, href_urls) -> set:
        urls = set()
        checked_key = set()

        for href_url in href_urls:
            parsed_parts = urlparse(href_url)
            if self._url_ignore_ext_regex.search(parsed_parts.path):
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

    def __is_date(self, string):
        try:
            datetime.strptime(string, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def __is_valid_hash(self, string):

        if re.match(r'^[a-f0-9]{32}$', string):
            return True
        if re.match(r'^[a-f0-9]{16}$', string):
            return True
        try:
            uuid_obj = uuid.UUID(string)
            return str(uuid_obj) == string
        except ValueError:
            return False
