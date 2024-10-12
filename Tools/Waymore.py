import os
from datetime import datetime
from typing import List
from urllib.parse import urlparse

import inject

from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.Constants import URL_IGNORE_EXT_REGEX, VALID_STATUSES
from Models.HeadRequestDTO import HeadRequestDTO


class Waymore:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._head_dtos: List[HeadRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)
        self._checked_hrefs = set()
        self._out_of_scope = os.environ.get("out_of_scope")
        self._wayback_max_size = 50000
        self._request_handler = inject.instance(RequestHandler)
        self._request_checker = inject.instance(RequestChecker)
        self._process_handler = inject.instance(ProcessHandler)
        self._logger = inject.instance(Logger)
        self._thread_man = inject.instance(ThreadManager)

    def get_domains(self, domain: str) -> set:
        cache_manager = CacheHelper(f'{self._tool_name}_domains', domain)
        result = cache_manager.get_saved_result()
        if result is None:

            out_of_scope = [x for x in self._out_of_scope.split(';') if x]
            if any(oos in domain for oos in out_of_scope):
                self._logger.log_warn(f'({domain}) out of scope waymore')
                return set()
            result = self.__get_domains(domain)
            cache_manager.cache_result(result)

        self._logger.log_info(f'({domain}) {self._tool_name} found {len(result)} items')
        return result

    def get_requests_dtos(self, domain) -> List[HeadRequestDTO]:
        cache_manager = CacheHelper(f'{self._tool_name}_urls', domain)
        result = cache_manager.get_saved_result()
        if result is None:

            out_of_scope = [x for x in self._out_of_scope.split(';') if x]
            if any(oos in domain for oos in out_of_scope):
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) out of scope waymore')
                return []
            result = self.__get_urls(domain)
            cache_manager.cache_result(result)

        self._logger.log_info(f'({domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_domains(self, domain: str) -> set:
        res_file = f'{self._tool_result_dir}/{domain.replace(":", "_")}.txt'
        if not os.path.exists(res_file):
            cmd = ["python", "/root/Desktop/TOOLs/waymore/waymore.py", "-i", domain, "-oU", res_file,
                   "-mode", "U", "-t", "10"]

            self._process_handler.run_temp_process(cmd, 'waymore')

        domains = set()
        text_file = open(res_file, 'r', encoding='utf-8', errors='ignore')
        lines = text_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if domain in netloc:
                domains.add(netloc)
        text_file.close()

        return domains

    def __get_urls(self, domain: str) -> List[HeadRequestDTO]:
        res_file = f'{self._tool_result_dir}/{domain.replace(":", "_")}.txt'

        if not os.path.exists(res_file):
            cmd = ["python", "/root/Desktop/TOOLs/waymore/waymore.py", "-i", domain, "-oU", res_file,
                   "-mode", "U", "-t", "5"]

            self._process_handler.run_temp_process(cmd, 'waymore')

        if not os.path.exists(res_file):
            return self._head_dtos

        href_urls = set()
        text_file = open(res_file, 'r', encoding='utf-8', errors='ignore')
        lines = text_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if domain in netloc:
                href_urls.add(line)
        text_file.close()

        urls = self.__filter_urls(href_urls)

        self._thread_man.run_all(self.__check_href_urls, urls, debug_msg=f'{self._tool_name} ({domain})')

        return self._head_dtos

    def __check_href_urls(self, url: str):
        url_parts = urlparse(url)
        if url_parts.path in self._checked_hrefs or URL_IGNORE_EXT_REGEX.search(url):
            return
        else:
            self._checked_hrefs.add(url_parts.path)

        response = self._request_handler.send_head_request(url)
        if response is None:
            return

        if response.status_code in VALID_STATUSES:
            self._head_dtos.append(HeadRequestDTO(response))

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

            split_path = [item for item in urlparse(url_without_params).path.split('/') if item]
            path_key = ''
            for part in split_path:
                if part.isdigit():
                    path_key += 'numb'
                elif self._request_checker.is_valid_hash(part):
                    path_key += 'guid'
                elif self._request_checker.is_date(part):
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
