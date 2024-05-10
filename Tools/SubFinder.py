import os
from datetime import datetime

from Helpers.CacheHelper import CacheHelper


class SubFinder:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def get_subdomains(self, avoid_cache=False) -> set:
        cache_manager = CacheHelper(self.__tool_name, self.__domain)
        subdomains = cache_manager.get_saved_result()
        if (not subdomains and not isinstance(subdomains, set)) or avoid_cache:
            subdomains = set()
            command = f'subfinder -d {self.__domain} -silent'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if self.__domain in line:
                    subdomains.add(line.replace('\n', ''))
            cache_manager.cache_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(subdomains)} items')
        return subdomains
