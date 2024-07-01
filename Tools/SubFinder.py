import os
from datetime import datetime

from Helpers.CacheHelper import CacheHelper


class SubFinder:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain

    def get_subdomains(self, avoid_cache=False) -> set:
        cache_manager = CacheHelper(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if (not subdomains and not isinstance(subdomains, set)) or avoid_cache:
            subdomains = set()
            command = f'subfinder -d {self._domain} -silent'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if line.endswith(self._domain):
                    subdomains.add(line.replace('\n', ''))
                elif self._domain in line:
                    print(f'{line} subfinder found not added')

            cache_manager.cache_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains
