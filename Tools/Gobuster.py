import os
import subprocess
from datetime import datetime
from threading import Timer
from urllib.parse import urlparse
from Managers.CacheManager import CacheManager


class Gobuster:
    def __init__(self, domain, headers, raw_cookies):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._raw_cookies = raw_cookies
        self._headers = headers
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._cache_manager = CacheManager(self._tool_name, domain)

    def check_single_url(self, url):
        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:
            try:
                then = datetime.now()

                parsed_parts = urlparse(url)
                base_url = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'

                print(f'[{then.strftime("%H:%M:%S")}]: Gobuster {base_url} start...')

                output_file = f'{self._tool_result_dir}/RAW_{self._domain}.txt'
                cmd_arr = ["gobuster", "dir",
                           "-u", base_url,
                           "-w", f"{self._app_wordlists_path}ExploitDB.txt",
                           "-H", f"User-Agent:{self._headers['User-Agent']}",
                           "--no-error", "-t", "50", "-o", output_file]

                if len(self._raw_cookies) > 0:
                    cmd_arr.append("-c")
                    cmd_arr.append(self._raw_cookies)

                proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                kill_action = lambda process: process.kill()
                my_timer = Timer(1200, kill_action, [proc])
                try:
                    my_timer.start()
                    proc.wait()
                    msg = proc.stderr.read().decode()
                    print(f'({base_url}); '
                          f'msg - {msg}; '
                          f'cmd - gobuster dir -u {base_url} -w {self._app_wordlists_path}ExploitDB.txt --no-error -t 50')

                    if 'Error: ' in msg and ' => ' in msg:

                        status_code = msg.split(' => ', 1)[1].split(' (', 1)[0]
                        length_to_exclude = msg.split('Length: ', 1)[1].split(')', 1)[0]
                        if status_code.isdigit() and status_code != '200':
                            print(f'Status will be excluded: {status_code}')
                            cmd_arr.append('-b')
                            cmd_arr.append(f'{status_code},404')
                        elif length_to_exclude.isdigit():
                            print(f'Length will be excluded: {length_to_exclude}')
                            cmd_arr.append('-b')
                            cmd_arr.append('404')
                            cmd_arr.append('--exclude-length')
                            cmd_arr.append(length_to_exclude)
                        else:
                            print(f"Gobuster error - {status_code} is not a status code")
                        my_timer.cancel()

                        proc2 = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        kill_action2 = lambda process: process.kill()
                        my_timer = Timer(600, kill_action2, [proc2])
                        my_timer.start()
                        proc2.wait()
                        final_msg = proc2.stderr.read().decode()
                        print(f'({base_url}); Final message: {final_msg}; ')

                finally:
                    my_timer.cancel()

                if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                    os.remove(output_file)

                print(f'[{datetime.now().strftime("%H:%M:%S")}]: Gobuster {url} finished.')
                duration = datetime.now() - then
                self._cache_manager.save_result([f'Gobuster finished in {duration.total_seconds()} seconds'])
            except Exception as inst:
                self._cache_manager.save_result([f'Gobuster finished with ERRORS in ({inst})'])
