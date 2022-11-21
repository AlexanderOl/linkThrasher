import os
from datetime import datetime

from Managers.CacheManager import CacheManager


class SubFinder:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains:
            subdomains = set()
            command = f'subfinder -d {self.__domain} -silent'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if self.__domain in line:
                    subdomains.add(line.replace('\n', ''))
            cache_manager.save_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(subdomains)} items')
        return subdomains
