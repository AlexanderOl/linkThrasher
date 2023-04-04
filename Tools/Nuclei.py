import os
import pathlib
import re
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO


class Nuclei:
    def __init__(self, cache_key, headers, raw_cookies=''):
        self._tool_name = self.__class__.__name__
        self._cache_key = cache_key
        self._headers = headers
        self._raw_cookies = raw_cookies
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._cache_manager = CacheManager(self._tool_name, cache_key)
        self._expected = ['[medium]', '[high]', '[critical]', '[unknown]', '[network]']
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._chunk_size = 30
        self._main_txt_filepath = f"{self._tool_result_dir}/MAIN_{self._cache_key}.txt"

    def check_multiple_uls(self, get_dtos: List[GetRequestDTO]):

        report_lines = self._cache_manager.get_saved_result()
        if not report_lines and not isinstance(report_lines, List):

            batches = list(self.__divide_chunks(get_dtos))
            counter = len(batches)
            for dtos_batch in batches:
                self.__check_batch(dtos_batch, counter)
                counter -= 1
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(dtos_batch)}')

            if os.path.exists(self._main_txt_filepath):
                main_txt_file = open(self._main_txt_filepath, 'r')
                report_lines = main_txt_file.readlines()

            self.__cleanup(len(batches))

            self._cache_manager.save_result(report_lines)

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
                      f"-t /root/Desktop/TOOLs/nuclei-templates/fuzzing/ " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/vulnerabilities " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/cves " \
                      f"-t /root/Desktop/TOOLs/nuclei-templates/cnvd " \
                      f"-et /root/Desktop/TOOLs/nuclei-templates/cves/2022/CVE-2022-45362.yaml"
            stream = os.popen(command)
            bash_outputs = stream.readlines()

            result = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                for keyword in self._expected:
                    if keyword in encoded_line:
                        result.add(encoded_line)
                print(line)

            self._cache_manager.save_result(result)

    def __check_batch(self, dtos_batch: List[GetRequestDTO], counter):
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
                  f"-t /root/Desktop/TOOLs/nuclei-templates/fuzzing/ " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/vulnerabilities " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/cves " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/cnvd " \
                  f"-t /root/Desktop/TOOLs/nuclei-templates/miscellaneous" \
                  f"-et /root/Desktop/TOOLs/nuclei-templates/cves/2022/CVE-2022-45362.yaml"

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
