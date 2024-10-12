import os
from datetime import datetime
from urllib.parse import urlparse

import inject

from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper
from Models.Constants import HEADERS


class Gobuster:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._threads = f'{os.environ.get("threads")}'
        self._status_codes_to_avoid = ['400', '404', '429']
        self._logger = inject.instance(Logger)
        self._cookie_manager = inject.instance(CookieHelper)
        self._process_handler = inject.instance(ProcessHandler)

    def check_single_url(self, url):
        domain = urlparse(url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        report_lines = cache_manager.get_saved_result()
        if not report_lines:
            try:
                then = datetime.now()

                parsed_parts = urlparse(url)
                base_url = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'

                self._logger.log_info(f'Gobuster {base_url} start...')

                if not os.path.exists(self._tool_result_dir):
                    os.makedirs(self._tool_result_dir)

                output_file = f'{self._tool_result_dir}/{domain.replace(":", "_")}.txt'
                cmd_arr = ["gobuster", "dir",
                           "-b", "400,404,429",
                           "-u", base_url,
                           "-w", f"{self._app_wordlists_path}gobuster.txt",
                           "-H", f"User-Agent:{HEADERS['User-Agent']}",
                           "--no-error", "-t", str(self._threads), "-k",
                           "-o", output_file]

                raw_cookies = self._cookie_manager.get_raw_cookies(domain)

                if len(raw_cookies) > 0:
                    cmd_arr.append("-c")
                    cmd_arr.append(raw_cookies)

                lines = self._process_handler.run_temp_process(cmd_arr, url)
                for proc_msg in lines:
                    if 'Error: ' in proc_msg and ' => ' in proc_msg:

                        status_code = proc_msg.split(' => ', 1)[1].split(' (', 1)[0]
                        length_to_exclude = proc_msg.split('Length: ', 1)[1].split(')', 1)[0]
                        if (status_code.isdigit() and status_code != '200'
                                and status_code not in self._status_codes_to_avoid):
                            self._logger.log_info(f'Gobuster status will be excluded: {status_code}')
                            cmd_arr.append('-b')
                            cmd_arr.append(f'{status_code},{",".join(self._status_codes_to_avoid)}')
                        elif length_to_exclude.isdigit():
                            self._logger.log_info(f'Gobuster length will be excluded: {length_to_exclude}')
                            cmd_arr.append('-b')
                            cmd_arr.append(','.join(self._status_codes_to_avoid))
                            cmd_arr.append('--exclude-length')
                            cmd_arr.append(length_to_exclude)
                        else:
                            self._logger.log_info(f"Gobuster error - {status_code} is not a status code")

                        proc_msgs = self._process_handler.run_temp_process(cmd_arr, url)
                        msg = next((s for s in proc_msgs if f'Finished' in s), '<empty>')
                        self._logger.log_info(f'({base_url}); Final message: {msg}; ')
                        break

                if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                    os.remove(output_file)

                main_txt_file = open(output_file, 'r', encoding='utf-8', errors='ignore')
                report_lines = main_txt_file.readlines()
                result_lines = []
                unique_keys = {}
                for line in report_lines:
                    split = list(filter(None, line.split('(Status: ')))
                    if len(split) >= 2:
                        key = f"{split[1].split('-->')[0]}"
                        if key not in unique_keys:
                            unique_keys[key] = 0
                        if unique_keys[key] >= 5:
                            continue
                        unique_keys[key] += 1
                        result_lines.append(line)

                if len(result_lines) == 0:
                    os.remove(output_file)
                    return []

                txt_file = open(output_file, 'w')
                for line in result_lines:
                    txt_file.write(line)
                txt_file.close()

                self._logger.log_info(f'[{datetime.now().strftime("%H:%M:%S")}]: Gobuster {url} finished.')
                duration = datetime.now() - then
                cache_manager.cache_result([f'Gobuster finished in {duration.total_seconds()} seconds'])
            except Exception as inst:
                cache_manager.cache_result([f'Gobuster finished with ERRORS in ({inst})'])
