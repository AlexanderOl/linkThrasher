import os
import pathlib
import re
from datetime import datetime
from typing import List
import urllib.parse as urlparse

from Common.CollectionUtil import CollectionUtil
from Helpers.CacheHelper import CacheHelper
from Models.HeadRequestDTO import HeadRequestDTO


class Nuclei:
    def __init__(self, cache_key: str, headers, raw_cookies=''):
        self._tool_name = self.__class__.__name__
        self._cache_key = cache_key.replace(':', '_')
        self._headers = headers
        self._raw_cookies = raw_cookies
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._tool_result_fuzzing_dir = f'{self._tool_result_dir}_fuzzing'
        self._cache_manager = CacheHelper(self._tool_name, cache_key, 'Results')
        self._expected = ['[info]', '[medium]', '[high]', '[critical]', '[unknown]', '[network]']
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._chunk_size = 30
        self._main_txt_filepath = f"{self._tool_result_dir}/MAIN_{self._cache_key}.txt"
        self._main_txt_fuzzing_filepath = f"{self._tool_result_fuzzing_dir}/MAIN_{self._cache_key}.txt"
        self._already_added_pathes = {}

    def fuzz_batch(self, head_dtos: List[HeadRequestDTO]):

        if not os.path.exists(self._tool_result_fuzzing_dir):
            os.makedirs(self._tool_result_fuzzing_dir)

        if os.path.isfile(self._main_txt_fuzzing_filepath):
            return

        report_lines = self._cache_manager.get_saved_result()
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

        txt_filepath = f"{self._tool_result_fuzzing_dir}/{self._cache_key}.txt"
        if os.path.exists(txt_filepath):
            print(f"File found: {txt_filepath}")
            return

        txt_file = open(txt_filepath, 'w')
        for url in get_result:
            txt_file.write(f"{url}\n")
        txt_file.close()

        filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
        command = f"nuclei --list {filepath} -t /root/Desktop/TOOLs/fuzzing-templates "

        stream = os.popen(command)
        bash_outputs = stream.readlines()

        main_txt_file = open(self._main_txt_fuzzing_filepath, 'w')
        for line in bash_outputs:
            encoded_line = self._ansi_escape.sub('', line)
            for keyword in self._expected:
                if keyword in encoded_line:
                    main_txt_file.write(f"{encoded_line}")
            print(line)
        main_txt_file.close()

        if os.path.exists(self._main_txt_fuzzing_filepath):
            main_txt_file = open(self._main_txt_fuzzing_filepath, 'r')
            report_lines = set(main_txt_file.readlines())
            self._cache_manager.save_lines(report_lines)
            os.remove(self._main_txt_fuzzing_filepath)

        if os.path.exists(filepath):
            os.remove(filepath)

    def check_multiple_uls(self, get_dtos: List[HeadRequestDTO]):

        if not os.path.exists(self._tool_result_fuzzing_dir):
            os.makedirs(self._tool_result_fuzzing_dir)

        report_lines = self._cache_manager.get_saved_result()
        if not report_lines and not isinstance(report_lines, set):
            report_lines = set()
            batches = CollectionUtil.divide_chunks(get_dtos, self._chunk_size)
            counter = len(batches)
            for dtos_batch in batches:
                self.__check_batch(dtos_batch, counter)
                counter -= 1
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(dtos_batch)}')

            if os.path.exists(self._main_txt_filepath):
                main_txt_file = open(self._main_txt_filepath, 'r', encoding='utf-8', errors='ignore')
                report_lines = set(main_txt_file.readlines())

            self.__cleanup(len(batches))

            self._cache_manager.save_lines(report_lines)

    def __divide_chunks(self, items):
        items_to_split = list(items)
        for i in range(0, len(items_to_split), self._chunk_size):
            yield items_to_split[i:i + self._chunk_size]

    def check_single_url(self, url):
        report_lines = self._cache_manager.get_saved_result()
        if not report_lines and not isinstance(report_lines, set):

            agent = self._headers['User-Agent']
            header_args = f'-H "User-Agent:{agent})"'
            if len(self._raw_cookies) > 0:
                header_args += f' -H "Cookies:{self._raw_cookies}"'

            command = f"nuclei -u {url} {header_args} " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/fuzzing " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/vulnerabilities " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/miscellaneous " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/exposures " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/takeovers " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/cves " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/cnvd " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/cves/2022/CVE-2022-45362.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/missing-csp.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/missing-hsts.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/display-via-header.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/missing-x-frame-options.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/detect-dns-over-https.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/tabnabbing-check.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/email-extractor.yaml " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/google-floc-disabled.yaml "

            stream = os.popen(command)
            bash_outputs = stream.readlines()

            result = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                for keyword in self._expected:
                    if keyword in encoded_line:
                        result.add(encoded_line)
                print(line)

            self._cache_manager.save_lines(result)

    def __check_batch(self, dtos_batch: List[HeadRequestDTO], counter):

        txt_filepath = f"{self._tool_result_dir}/{self._cache_key}_{counter}.txt"
        if os.path.exists(txt_filepath):
            print(f"File found: {txt_filepath}")
            return

        txt_file = open(txt_filepath, 'w')
        for dto in dtos_batch:
            txt_file.write(f"{dto.url}\n")
        txt_file.close()

        filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)

        command = f"nuclei --list {filepath} " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/fuzzing " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/fuzzing " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/vulnerabilities " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/miscellaneous " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/exposures " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/takeovers " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/cves " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/cnvd " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/cves/2022/CVE-2022-45362.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/missing-csp.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/missing-hsts.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/display-via-header.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/missing-x-frame-options.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/detect-dns-over-https.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/tabnabbing-check.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/email-extractor.yaml " \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/miscellaneous/google-floc-disabled.yaml "

        stream = os.popen(command)
        bash_outputs = stream.readlines()

        main_txt_file = open(self._main_txt_filepath, 'a')
        for line in bash_outputs:
            encoded_line = self._ansi_escape.sub('', line)
            for keyword in self._expected:
                if keyword in encoded_line:
                    main_txt_file.write(f"{encoded_line}")
            print(line)
        main_txt_file.close()

    def __cleanup(self, length):
        for i in range(0, length + 1):
            filepath = f"{self._tool_result_dir}/{self._cache_key}_{i}.txt"
            if os.path.exists(filepath):
                os.remove(filepath)
        if os.path.exists(self._main_txt_filepath):
            os.remove(self._main_txt_filepath)

    def __check_if_added(self, url):
        is_already_added = False
        parsed = urlparse.urlparse(url)
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
