import os
import inject

from typing import List
from urllib.parse import urlparse
from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper


class Feroxbuster:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._max_depth = int(f'{os.environ.get("max_depth")}')
        self._threads = f'{os.environ.get("threads")}'
        self._process_handler = inject.instance(ProcessHandler)
        self._cookie_manager = inject.instance(CookieHelper)
        self._logger = inject.instance(Logger)

    def check_single_url(self, url) -> set[str]:
        domain = urlparse(url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        ready_urls = cache_manager.get_saved_result()

        if not ready_urls and not isinstance(ready_urls, set):

            report_lines = self.__run_tool_cmd(domain, url)
            ready_urls = self.__get_ready_urls(domain, report_lines)
            cache_manager.cache_result(ready_urls)

        return ready_urls

    def __run_tool_cmd(self, domain, url) -> [str]:

        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

        output_file = f'{self._tool_result_dir}/RAW_{domain.replace(":", "_")}.txt'
        cmd = ["feroxbuster", "--url", url, "-w", f"{self._app_wordlists_path}directories.txt", "-o", output_file,
               "--insecure", "--no-state", "--threads", str(self._threads), "--auto-bail"]

        raw_cookies = self._cookie_manager.get_raw_cookies(domain)

        if len(raw_cookies) > 0:
            cmd.append("-b")
            cmd.append(raw_cookies)

        self._logger.log_info(f'({url}) Feroxbuster starts...')

        self._process_handler.run_temp_process(cmd, url)

        result_lines = self.__parse_output(output_file)

        cewl_file = f'{self._tool_result_dir}/CEWL_{domain.replace(":", "_")}.txt'

        cmd = ["cewl",  url, "-d", str(self._max_depth), "-w", cewl_file]
        self._logger.log_info(f'({url}) CEWL starts...')

        self._process_handler.run_temp_process(cmd, url)

        if os.path.exists(cewl_file):
            output_file = f'{self._tool_result_dir}/RAW_CEWL_{domain.replace(":", "_")}.txt'
            cmd = ["feroxbuster", "--url", url, "-w", cewl_file, "-o", output_file,
                   "-x", "asmx ashx txt conf config bak bkp cache swp old db aspx aspx~ asp asp~ py py~ rb rb~ "
                         "jsp jsp~ php php~ cgi csv html inc jar js json lock log rar sql sql~ swp swp~ tar tar.gz "
                         "wsdl wadl zip xml",
                   "--insecure", "--no-state", "--threads", str(self._threads), "--auto-bail"]

            self._process_handler.run_temp_process(cmd, url)

            cewl_lines = self.__parse_output(output_file)
            result_lines.update(cewl_lines)

            os.remove(cewl_file)

        self._logger.log_info(f'({url}) Feroxbuster finished!')

        if len(result_lines) > 0:
            txt_file = open(f'{self._tool_result_dir}/{domain.replace(":", "_")}.txt', 'w')
            for line in result_lines:
                txt_file.write(line)
            txt_file.close()

        return result_lines

    def __get_ready_urls(self, domain: str, report_lines: List[str]) -> set:
        filtered_output = set()

        for line in report_lines:

            if (line.startswith('200') or 'Got 200' in line) and 'http' in line:
                index = line.find('http')
                url = line[index:]
                parsed = urlparse(url)
                if domain in parsed.netloc:
                    filtered_output.add(url.strip())
            elif ' => ' in line:
                redirect = line.split(' => ', 1)[1]
                if redirect.startswith('http'):
                    parsed = urlparse(redirect)
                    if domain in parsed.netloc:
                        filtered_output.add(redirect.strip())
                elif redirect.strip().endswith('/'):
                    index = line.find('http')
                    url = f'{line[index:].split(" ")[0]}/'
                    parsed = urlparse(url)
                    if domain in parsed.netloc:
                        filtered_output.add(url.strip())

            elif 'http' in line:
                index = line.find('http')
                redirected_url = line[index:]
                parsed = urlparse(redirected_url)
                if domain in parsed.netloc:
                    filtered_output.add(redirected_url.strip())
            else:
                self._logger.log_warn(f'FEROXBUSTER error! Unable to parse - ({line})')

        return filtered_output

    @staticmethod
    def __parse_output(output_file) -> set:

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
