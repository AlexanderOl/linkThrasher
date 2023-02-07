import os
import subprocess
from datetime import datetime
from threading import Timer

from Managers.CacheManager import CacheManager


class Dirb:
    def __init__(self, domain):
        self.cache_manager = CacheManager(self.__class__.__name__, domain)

    def check_single_url(self, url):

        report_lines = self.cache_manager.get_saved_result()
        if not report_lines:

            proc = subprocess.Popen(["dirb", url, "-r", "-f"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            kill_action = lambda process: process.kill()
            my_timer = Timer(600, kill_action, [proc])

            try:
                my_timer.start()
                proc.wait()
                bash_outputs = proc.stderr.read().decode()

                print(f'({url}) err_message - {bash_outputs}')

                if len(bash_outputs) == 0 and not url.startswith('https:'):
                    url = url.replace('http:', 'https:')
                    my_timer.cancel()
                    self.check_single_url(url)

                filtered_output = list(filter(lambda o: 'CODE:2' in o or 'DIRECTORY:' in o, bash_outputs))
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb {url} finished. Found {len(filtered_output)}')
                self.cache_manager.save_result(filtered_output)

            finally:
                my_timer.cancel()


