import os
from datetime import datetime
from urllib.parse import urlparse
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper


class Gobuster:
    def __init__(self, domain: str, headers, raw_cookies):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._raw_cookies = raw_cookies
        self._headers = headers
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._threads = f'{os.environ.get("threads")}'
        self._cache_manager = CacheHelper(self._tool_name, domain)

    def check_single_url(self, url):
        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:
            try:
                then = datetime.now()

                parsed_parts = urlparse(url)
                base_url = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'

                print(f'[{then.strftime("%H:%M:%S")}]: Gobuster {base_url} start...')

                if not os.path.exists(self._tool_result_dir):
                    os.makedirs(self._tool_result_dir)

                output_file = f'{self._tool_result_dir}/{self._domain.replace(":","_")}.txt'
                cmd_arr = ["gobuster", "dir"
                           "-b", "400-429",
                           "-u", base_url,
                           "-w", f"{self._app_wordlists_path}gobuster.txt",
                           "-H", f"User-Agent:{self._headers['User-Agent']}",
                           "--no-error", "-t", str(self._threads), "-k",
                           "-o", output_file]

                if len(self._raw_cookies) > 0:
                    cmd_arr.append("-c")
                    cmd_arr.append(self._raw_cookies)

                pk = ProcessHandler()
                lines = pk.run_temp_process(cmd_arr, url)
                for proc_msg in lines:
                    if 'Error: ' in proc_msg and ' => ' in proc_msg:

                        status_code = proc_msg.split(' => ', 1)[1].split(' (', 1)[0]
                        length_to_exclude = proc_msg.split('Length: ', 1)[1].split(')', 1)[0]
                        if status_code.isdigit() and status_code != '200':
                            print(f'Gobuster status will be excluded: {status_code}')
                            cmd_arr.append('-b')
                            cmd_arr.append(f'{status_code},404')
                        elif length_to_exclude.isdigit():
                            print(f'Gobuster length will be excluded: {length_to_exclude}')
                            cmd_arr.append('-b')
                            cmd_arr.append('404')
                            cmd_arr.append('--exclude-length')
                            cmd_arr.append(length_to_exclude)
                        else:
                            print(f"Gobuster error - {status_code} is not a status code")

                        proc_msgs = pk.run_temp_process(cmd_arr, url)
                        msg = next((s for s in proc_msgs if f'Finished' in s), '<empty>')
                        print(f'({base_url}); Final message: {msg}; ')
                        break

                if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                    os.remove(output_file)

                main_txt_file = open(output_file, 'r')
                report_lines = main_txt_file.readlines()
                result_lines = []
                unique_keys = {}
                for line in report_lines:
                    split = list(filter(None, line.split('(Status: ')))
                    if len(split) >= 2:
                        key = f"{split[-1]}"
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

                print(f'[{datetime.now().strftime("%H:%M:%S")}]: Gobuster {url} finished.')
                duration = datetime.now() - then
                self._cache_manager.save_result([f'Gobuster finished in {duration.total_seconds()} seconds'])
            except Exception as inst:
                self._cache_manager.save_result([f'Gobuster finished with ERRORS in ({inst})'])
