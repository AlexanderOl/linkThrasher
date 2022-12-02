import os
from datetime import datetime

from Managers.CacheManager import CacheManager


class Sublister:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):
            subdomains = set()
            command = f'cd /root/Desktop/TOOLs/Sublist3r/; python sublist3r.py -d {self.__domain} | ' \
                      f'grep "Total Unique Subdomains Found" -A 999'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            skip_first_line = True
            for line in bash_outputs:
                if skip_first_line:
                    skip_first_line = False
                    continue
                subdomains.add(line.replace('\x1b[92m', '').replace('\x1b[0m\n', ''))
            cache_manager.save_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(subdomains)} items')
        return subdomains
