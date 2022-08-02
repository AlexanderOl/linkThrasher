import os
from datetime import datetime

from Managers.CacheManager import CacheManager
from Managers.ThreadManager import ThreadManager


class Dirb:
    def __init__(self, thread_man: ThreadManager):
        self._thread_man = thread_man
        self.cache_manager = CacheManager('Dirb', 'FOUND')

    def check_subdomain_urls(self, urls):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb started...')

        self._thread_man.run_all(urls, self.__run_dirb_cmd)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb FINISHED {len(urls)} urls')

    def __run_dirb_cmd(self, url):
        command = f"dirb {url} -r -f"
        stream = os.popen(command)
        bash_outputs = stream.readlines()

        if len(bash_outputs) == 0 and 'https' not in url:
            url = url.replace('http', 'https')
            self.__run_dirb_cmd(url)
        filtered_output = list(filter(lambda o: 'CODE:200' in o or 'DIRECTORY:' in o, bash_outputs))
        print(f'Dirb {url} finished. Found {len(filtered_output)}')
        self.cache_manager.save_result(filtered_output)

