import os
import re
import uuid
from datetime import datetime
from typing import List
from urllib.parse import urlparse

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
            '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.ashx$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
            '|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.mp4$|\.avi$|\.mp3$|\.webp$',
            re.IGNORECASE)
        self._result: List[HeadRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._checked_hrefs = set()
        self._waybackurls_out_of_scope_domains = os.environ.get("waybackurls_out_of_scope_domains")

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
        path_without_digits = set()
        added_url_params = {}

        for href_url in href_urls:
            parsed_parts = urlparse(href_url)
            url_without_params = f'{parsed_parts.scheme}://{parsed_parts.netloc}{parsed_parts.path}'.lower()
            query_params = {}
            if self._url_ignore_ext_regex.search(parsed_parts.path):
                continue
            if '?' in href_url:
                params = parsed_parts.query.split('&')
                for param in params:
                    split = param.split('=')
                    if len(split) == 2:
                        query_params[split[0]] = split[1]

            if url_without_params in added_url_params:
                added_url_params[url_without_params].update(query_params)
            else:
                added_url_params[url_without_params] = query_params

        for url_without_params in added_url_params:
            params = added_url_params[url_without_params]
            url = url_without_params

            split_path = url_without_params.split('/')
            path_key = ''
            for part in split_path:
                if part.isdigit():
                    path_key += 'numb'
                elif self.__is_valid_uuid(part):
                    path_key += 'guid'
                elif self.__is_date(part):
                    path_key += 'date'
                else:
                    path_key += part
            if path_key in path_without_digits:
                continue
            else:
                path_without_digits.add(path_key)

            if len(params) > 0:
                url += '?'

            for key in params:
                url += f'{key}={params[key]}'
            urls.add(url)

        return urls

    def __is_valid_uuid(self, uuid_string):
        try:
            uuid_obj = uuid.UUID(uuid_string)
            return str(uuid_obj) == uuid_string
        except ValueError:
            return False

    def __is_date(self, string):
        try:
            # Attempt to parse the string into a datetime object
            datetime.strptime(string, '%Y-%m-%d')
            return True
        except ValueError:
            # If parsing fails, it's not a valid date
            return False
