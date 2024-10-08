import os
import re
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from Common.ProcessHandler import ProcessHandler
from Common.RequestChecker import RequestChecker
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Feroxbuster:
    def __init__(self, domain, request_handler: RequestHandler, raw_cookies):
        self._form_dtos: List[FormRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._head_dtos: List[HeadRequestDTO] = []
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheHelper(self._tool_name, domain)
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._max_depth = int(f'{os.environ.get("max_depth")}')
        self._threads = f'{os.environ.get("threads")}'
        self._request_handler = request_handler
        self._request_checker = RequestChecker()
        self._raw_cookies = raw_cookies
        self._url_ignore_ext_regex = re.compile(
            '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.ashx$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
            '|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.mp4$|\.avi$|\.mp3$',
            re.IGNORECASE)
        self._valid_statuses = [200, 204, 301, 302, 307, 308, 401, 403, 405, 500]

    def check_single_url(self, url,
                         already_exist_head_dtos: List[HeadRequestDTO],
                         already_exist_form_dtos: List[FormRequestDTO]):

        dtos = self._cache_manager.get_saved_result()
        if not dtos and not isinstance(dtos, List):

            self._form_dtos = already_exist_form_dtos
            report_lines = self.__run_tool_cmd(url)

            ready_urls = self.__get_ready_urls(report_lines, already_exist_head_dtos)

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url, ready_urls, debug_msg=f'{self._tool_name} ({self._domain})')

            self._head_dtos.extend(already_exist_head_dtos)
            self._cache_manager.cache_result({'head_dtos': self._head_dtos, 'form_dtos': self._form_dtos})

        else:
            self._head_dtos = dtos['head_dtos']
            self._form_dtos = dtos['form_dtos']

        return self._head_dtos, self._form_dtos

    def __check_url(self, url):
        if self._url_ignore_ext_regex.search(url):
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({url}) Feroxbuster ignored')
            return

        check = self._request_handler.send_head_request(url)
        if check is None:
            return

        response = self._request_handler.handle_request(url, timeout=5)
        if response is None:
            return

        if (any(dto for dto in self._get_dtos
                if dto.status_code == response.status_code
                   and dto.response_length == len(response.text))
                or 'captcha' in response.text.lower()):
            return

        if response.status_code not in self._valid_statuses:
            return

        get_dtos = GetRequestDTO(url, response)
        self._get_dtos.append(get_dtos)
        self._head_dtos.append(HeadRequestDTO(response))
        if response.status_code == 200:
            form_dto = self._request_checker.find_forms(url, response.text, get_dtos, self._form_dtos)
            if form_dto:
                self._form_dtos.append(form_dto)

    def __run_tool_cmd(self, url) -> [str]:

        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

        output_file = f'{self._tool_result_dir}/RAW_{self._domain.replace(":", "_")}.txt'
        cmd = ["feroxbuster", "--url", url, "-w", f"{self._app_wordlists_path}directories.txt", "-o", output_file,
               "--insecure", "--no-state", "--threads", str(self._threads), "--auto-bail"]

        if len(self._raw_cookies) > 0:
            cmd.append("-b")
            cmd.append(self._raw_cookies)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({url}) Feroxbuster starts...')

        pk = ProcessHandler()
        pk.run_temp_process(cmd, url)

        result_lines = self._parse_output(output_file)

        cewl_file = f'{self._tool_result_dir}/CEWL_{self._domain.replace(":", "_")}.txt'

        cmd = ["cewl",  url, "-d", str(self._max_depth), "-w", cewl_file]
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({url}) CEWL starts...')
        pk = ProcessHandler()
        pk.run_temp_process(cmd, url)

        if os.path.exists(cewl_file):
            output_file = f'{self._tool_result_dir}/RAW_CEWL_{self._domain.replace(":", "_")}.txt'
            cmd = ["feroxbuster", "--url", url, "-w", cewl_file, "-o", output_file,
                   "-x", "asmx ashx txt conf config bak bkp cache swp old db aspx aspx~ asp asp~ py py~ rb rb~ jsp jsp~ php php~ cgi csv html inc jar js json lock log rar sql sql~ swp swp~ tar tar.gz wsdl wadl zip xml",
                   "--insecure", "--no-state", "--threads", str(self._threads), "--auto-bail"]
            pk = ProcessHandler()
            pk.run_temp_process(cmd, url)

            cewl_lines = self._parse_output(output_file)
            result_lines.update(cewl_lines)

            os.remove(cewl_file)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({url}) Feroxbuster finished!')

        if len(result_lines) > 0:
            txt_file = open(f'{self._tool_result_dir}/{self._domain.replace(":", "_")}.txt', 'w')
            for line in result_lines:
                txt_file.write(line)
            txt_file.close()

        return result_lines

    def __get_ready_urls(self, report_lines: List[str], already_exist_dtos: List[HeadRequestDTO]) -> set:
        filtered_output = set()

        for line in report_lines:

            if (line.startswith('200') or 'Got 200' in line) and 'http' in line:
                index = line.find('http')
                url = line[index:]
                parsed = urlparse(url)
                if self._domain in parsed.netloc:
                    filtered_output.add(url.strip())
            elif ' => ' in line:
                redirect = line.split(' => ', 1)[1]
                if redirect.startswith('http'):
                    parsed = urlparse(redirect)
                    if self._domain in parsed.netloc:
                        filtered_output.add(redirect.strip())
                elif redirect.strip().endswith('/'):
                    index = line.find('http')
                    url = f'{line[index:].split(" ")[0]}/'
                    parsed = urlparse(url)
                    if self._domain in parsed.netloc:
                        filtered_output.add(url.strip())

            elif 'http' in line:
                index = line.find('http')
                redirected_url = line[index:]
                parsed = urlparse(redirected_url)
                if self._domain in parsed.netloc:
                    filtered_output.add(redirected_url.strip())
            else:
                print(f'FEROXBUSTER error! Unable to parse - ({line})')

        already_exist_keys = (dto.key for dto in already_exist_dtos)
        ready_urls = set()
        checked_keys = set()
        for url in filtered_output:
            key = self._request_checker.get_url_key(url)
            if key not in already_exist_keys and key not in checked_keys:
                checked_keys.add(key)
                ready_urls.add(url)

        return ready_urls

    def _parse_output(self, output_file) -> set:

        report_lines = []
        if os.path.exists(output_file):
            main_txt_file = open(output_file, 'r')
            report_lines = main_txt_file.readlines()
            if os.path.getsize(output_file) == 0:
                os.remove(output_file)

        result_lines = set()
        unique_keys = {}
        for line in report_lines:
            split = list(filter(None, line.split(' ')))
            if len(split) > 4:
                key = f"{split[0]}_{split[1]}_{split[2]}_{split[3]}"
                if key not in unique_keys:
                    unique_keys[key] = 0
                if unique_keys[key] >= 5:
                    continue
                unique_keys[key] += 1
                result_lines.add(line)

        if os.path.exists(output_file):
            os.remove(output_file)

        return result_lines

