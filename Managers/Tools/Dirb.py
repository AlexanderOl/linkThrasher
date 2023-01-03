import os
from datetime import datetime

from Managers.CacheManager import CacheManager


class Dirb:
    def __init__(self, domain):
        self.cache_manager = CacheManager(self.__class__.__name__, domain)

    def check_single_url(self, url):

        report_lines = self.cache_manager.get_saved_result()
        if not report_lines:
            command = f"dirb {url} -r -f"
            stream = os.popen(command)
            bash_outputs = stream.readlines()

            if len(bash_outputs) == 0 and not url.startswith('https:'):
                url = url.replace('http:', 'https:')
                self.check_single_url(url)
            filtered_output = list(filter(lambda o: 'CODE:' in o or 'DIRECTORY:' in o, bash_outputs))
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb {url} finished. Found {len(filtered_output)}')
            self.cache_manager.save_result(filtered_output)
