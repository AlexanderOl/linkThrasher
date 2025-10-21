import os
import pathlib
import re
from datetime import datetime
from typing import List
from urllib.parse import urlparse

import inject

from Common.CollectionUtil import CollectionUtil
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper
from Models.Constants import HEADERS
from Models.HeadRequestDTO import HeadRequestDTO


class Nuclei:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._tool_result_fuzzing_dir = f'{self._tool_result_dir}_fuzzing'
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._chunk_size = 10
        self._already_added_pathes = {}
        self._template_args = ("-em http-missing-security-headers,"
                               "missing-hsts,"
                               "missing-csp,"
                               "cookies-without-secure,"
                               "xss-deprecated-header,"
                               "aws-cloudfront-service,"
                               "azure-domain-tenant,"
                               "httponly-cookie-detect,"
                               "http-trace,"
                               "aws-detect,"
                               "waf-detect,"
                               "cookies-without-httponly-secure,"
                               "akamai-detect,"
                               "akamai-cache-detect,"
                               "akamai-bot-manager-detect,"
                               "nginx-version,"
                               "aws-cloudfront-service,"
                               "apache-detect,"
                               "cors-misconfig,"
                               "form-detection,"
                               "favicon-detect,"
                               "apple-app-site-association,"
                               "google-floc-disabled,"
                               "security-txt "
                               "-ept dns,ssl "
                               "-et sri,dsl "
                               "-timeout 5 -irt 0m20s -nh")
        self._cookie_manager = inject.instance(CookieHelper)

    def fuzz_urls_batch(self, cache_key: str, head_dtos: List[HeadRequestDTO]):
        cache_key = cache_key.replace(':', '_')
        main_txt_fuzzing_filepath = f"{self._tool_result_fuzzing_dir}/MAIN_{cache_key}.txt"
        cache_manager = CacheHelper(self._tool_name, cache_key, 'Results')
        if not os.path.exists(self._tool_result_fuzzing_dir):
            os.makedirs(self._tool_result_fuzzing_dir)

        if os.path.isfile(main_txt_fuzzing_filepath):
            return

        report_lines = cache_manager.get_saved_result()
        if isinstance(report_lines, set):
            return

        get_result = set()
        checked_urls = set()
        for dto in head_dtos:

            is_added = self.__check_if_added(dto.url)
            if is_added:
                continue

            if '?' in dto.url:
                to_check = dto.url.split('?')[0]
                if to_check not in checked_urls:
                    checked_urls.add(to_check)
                    get_result.add(dto.url)

        if len(get_result) == 0:
            return

        txt_filepath = f"{self._tool_result_fuzzing_dir}/{cache_key}.txt"
        if os.path.exists(txt_filepath):
            print(f"File found: {txt_filepath}")
            return

        txt_file = open(txt_filepath, 'w')
        for url in get_result:
            txt_file.write(f"{url}\n")
        txt_file.close()

        filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
        command = f"nuclei --list {filepath} /root/Desktop/TOOLs/fuzzing-templates"

        stream = os.popen(command)
        bash_outputs = stream.readlines()

        main_txt_file = open(main_txt_fuzzing_filepath, 'w')
        for line in bash_outputs:
            encoded_line = self._ansi_escape.sub('', line)
            main_txt_file.write(f"{encoded_line}")
            print(line)
        main_txt_file.close()

        report_lines = set()
        if os.path.exists(main_txt_fuzzing_filepath):
            main_txt_file = open(main_txt_fuzzing_filepath, 'r')
            report_lines = set(main_txt_file.readlines())
            os.remove(main_txt_fuzzing_filepath)

        cache_manager.save_lines(report_lines)

        if os.path.exists(filepath):
            os.remove(filepath)

    def check_multiple_uls(self, cache_key, get_dtos: List[HeadRequestDTO]):
        cache_key = cache_key.replace(':', '_')
        cache_manager = CacheHelper(self._tool_name, cache_key, 'Results')
        if not os.path.exists(self._tool_result_fuzzing_dir):
            os.makedirs(self._tool_result_fuzzing_dir)

        report_lines = cache_manager.get_saved_result()
        if not report_lines and not isinstance(report_lines, set):
            report_lines = set()
            batches = CollectionUtil.divide_chunks(get_dtos, self._chunk_size)
            counter = len(batches)
            for dtos_batch in batches:
                self.__check_batch(cache_key, dtos_batch, counter)
                counter -= 1
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(dtos_batch)}')

            main_txt_filepath = f"{self._tool_result_dir}/MAIN_{cache_key}.txt"
            if os.path.exists(main_txt_filepath):
                main_txt_file = open(main_txt_filepath, 'r', encoding='utf-8', errors='ignore')
                report_lines = set(main_txt_file.readlines())

            for i in range(0, len(batches) + 1):
                filepath = f"{self._tool_result_dir}/{cache_key}_{i}.txt"
                if os.path.exists(filepath):
                    os.remove(filepath)
            if os.path.exists(main_txt_filepath):
                os.remove(main_txt_filepath)

            cache_manager.save_lines(report_lines)

    def __divide_chunks(self, items):
        items_to_split = list(items)
        for i in range(0, len(items_to_split), self._chunk_size):
            yield items_to_split[i:i + self._chunk_size]

    def check_single_url(self, url):
        cache_key = urlparse(url).netloc
        cache_key = cache_key.replace(':', '_')
        cache_manager = CacheHelper(self._tool_name, cache_key, 'Results')
        report_lines = cache_manager.get_saved_result()
        if not report_lines and not isinstance(report_lines, set):

            agent = HEADERS['User-Agent']
            header_args = f'-H "User-Agent:{agent})"'

            domain = urlparse(url).netloc
            raw_cookies = self._cookie_manager.get_raw_cookies(domain)

            if len(raw_cookies) > 0:
                header_args += f' -H "Cookies:{raw_cookies}"'

            command = f"nuclei -u {url} {header_args} {self._template_args}"

            stream = os.popen(command)
            bash_outputs = stream.readlines()

            result = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                result.add(encoded_line)
                print(line)

            cache_manager.save_lines(result)

    def __check_batch(self, cache_key: str, dtos_batch: List[HeadRequestDTO], counter):

        txt_filepath = f"{self._tool_result_dir}/{cache_key}_{counter}.txt"
        if os.path.exists(txt_filepath):
            print(f"File found: {txt_filepath}")
            return

        txt_file = open(txt_filepath, 'w')
        for dto in dtos_batch:
            txt_file.write(f"{dto.url}\n")
        txt_file.close()

        filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)

        command = f"nuclei --list {filepath} {self._template_args}"

        stream = os.popen(command)
        bash_outputs = stream.readlines()

        main_txt_filepath = f"{self._tool_result_dir}/MAIN_{cache_key}.txt"
        main_txt_file = open(main_txt_filepath, 'a')
        for line in bash_outputs:
            encoded_line = self._ansi_escape.sub('', line)
            main_txt_file.write(f"{encoded_line}")
            print(line)
        main_txt_file.close()

    def __check_if_added(self, url):
        is_already_added = False
        parsed = urlparse(url)
        params_to_check = filter(None, parsed.query.split("&"))
        key_to_check = ''
        for param_to_check in params_to_check:
            param_value_split = param_to_check.split('=')
            key_to_check += f'{param_value_split[0]};'

        added_path = self._already_added_pathes.get(parsed.path)
        if added_path:
            if key_to_check in added_path:
                is_already_added = True
            else:
                self._already_added_pathes[parsed.path].append(key_to_check)
        else:
            self._already_added_pathes[parsed.path] = [key_to_check]

        return is_already_added
