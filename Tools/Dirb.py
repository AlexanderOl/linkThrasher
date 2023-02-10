import os
import subprocess
from datetime import datetime
from threading import Timer

from Managers.CacheManager import CacheManager


class Dirb:
    def __init__(self, domain):
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheManager(self._tool_name, domain)
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'

    def check_single_url(self, url):

        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:

            output_file = f'{self._tool_result_dir}/RAW_{self._domain}.txt'
            proc = subprocess.Popen(["dirb", url, "-r", "-f", "-o", output_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            kill_action = lambda process: process.kill()
            my_timer = Timer(600, kill_action, [proc])

            try:
                my_timer.start()
                proc.wait()
                proc.stderr.read()

                main_txt_file = open(output_file, 'r')
                report_lines = main_txt_file.readlines()
                os.remove(output_file)

                if len(report_lines) == 0 and not url.startswith('https:'):
                    url = url.replace('http:', 'https:')
                    my_timer.cancel()
                    self.check_single_url(url)

                filtered_output = list(filter(lambda line: 'CODE:2' in line or 'DIRECTORY:' in line, report_lines))
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb {url} finished. Found {len(filtered_output)}')
                self._cache_manager.save_result(filtered_output)

            finally:
                if my_timer.is_alive():
                    my_timer.cancel()


