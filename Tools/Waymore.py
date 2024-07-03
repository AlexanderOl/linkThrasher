import os
import re
import uuid
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from Common.ProcessHandler import ProcessHandler
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.Constants import URL_IGNORE_EXT_REGEX, VALID_STATUSES
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Waymore:
    def __init__(self, domain, headers, cookies=''):
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._request_handler = RequestHandler(cookies, headers)
        self._result: List[HeadRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)
        self._checked_hrefs = set()
        self._out_of_scope_domains = os.environ.get("out_of_scope_domains")
        self._wayback_max_size = 50000
        self._request_checker = RequestChecker()

    def get_domains(self) -> set:
        cache_manager = CacheHelper(f'{self._tool_name}_domains', self._domain)
        result = cache_manager.get_saved_result()
        if result is None:

            out_of_scope = [x for x in self._out_of_scope_domains.split(';') if x]
            if any(oos in self._domain for oos in out_of_scope):
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) out of scope waymore')
                return set()
            result = self.__get_domains()
            cache_manager.cache_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(result)} items')
        return result

    def get_requests_dtos(self) -> List[HeadRequestDTO]:
        cache_manager = CacheHelper(f'{self._tool_name}_urls', self._domain)
        result = cache_manager.get_saved_result()
        if result is None:

            out_of_scope = [x for x in self._out_of_scope_domains.split(';') if x]
            if any(oos in self._domain for oos in out_of_scope):
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) out of scope waymore')
                return []
            result = self.__get_urls()
            cache_manager.cache_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_domains(self) -> set:
        res_file = f'{self._tool_result_dir}/{self._domain.replace(":", "_")}.txt'
        if not os.path.exists(res_file):
            cmd = ["python", "/root/Desktop/TOOLs/waymore/waymore.py", "-i", self._domain, "-oU", res_file,
                   "-mode", "U", "-t", "10"]
            pk = ProcessHandler()
            pk.run_temp_process(cmd, 'waymore')

        domains = set()
        text_file = open(res_file, 'r', encoding='utf-8', errors='ignore')
        lines = text_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if self._domain in netloc:
                domains.add(netloc)
        text_file.close()

        return domains

    def __get_urls(self) -> List[HeadRequestDTO]:
        res_file = f'{self._tool_result_dir}/{self._domain.replace(":", "_")}.txt'

        if not os.path.exists(res_file):
            cmd = ["python", "/root/Desktop/TOOLs/waymore/waymore.py", "-i", self._domain, "-oU", res_file,
                   "-mode", "U", "-t", "5"]
            pk = ProcessHandler()
            pk.run_temp_process(cmd, 'waymore')

        href_urls = set()
        text_file = open(res_file, 'r', encoding='utf-8', errors='ignore')
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
        if url_parts.path in self._checked_hrefs or URL_IGNORE_EXT_REGEX.search(url):
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

        if response.status_code in VALID_STATUSES:
            self._get_dtos.append(GetRequestDTO(url, response))
            self._result.append(HeadRequestDTO(response))

    def __filter_urls(self, href_urls) -> set:
        urls = set()
        path_without_digits = set()
        added_url_params = {}

        for href_url in href_urls:
            parsed_parts = urlparse(href_url)
            url_without_params = f'{parsed_parts.scheme}://{parsed_parts.netloc}{parsed_parts.path}'
            query_params = {}
            if URL_IGNORE_EXT_REGEX.search(parsed_parts.path):
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
                elif self.__is_valid_hash(part):
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

        if len(urls) > self._wayback_max_size:
            urls_with_params = set()
            for url_without_params in added_url_params:
                params = added_url_params[url_without_params]
                if len(params) == 0:
                    continue
                url = url_without_params
                for key in params:
                    url += f'{key}={params[key]}'
                urls_with_params.add(url)

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
