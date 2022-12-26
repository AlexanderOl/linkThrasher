import os
from datetime import datetime

from Managers.CacheManager import CacheManager


class Gobuster:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self.cache_manager = CacheManager(self._tool_name, domain)

    def check_single_url(self, url):
        report_lines = self.cache_manager.get_saved_result()
        if not report_lines:
            start = datetime.now()

            command = f"gobuster dir -u {url}  -w /usr/share/dirb/wordlists/big.txt -t 50 -o '{self._tool_result_dir}/{self._domain}.txt'"
            stream = os.popen(command)
            stream.read()

            finish = datetime.now()
            difference = finish - start
            difference_in_seconds = difference.total_seconds()

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: Gobuster {url} finished in {difference_in_seconds}')
            self.cache_manager.save_result([f'{url} finished in {difference_in_seconds}'])
