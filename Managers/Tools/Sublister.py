import os

from Managers.BaseSubdomainManager import BaseSubdomainManager
from Managers.CacheManager import CacheManager


class Sublister(BaseSubdomainManager):
    def __init__(self, domain, headers, download_path):
        super().__init__(domain, headers, download_path)
        self.__tool_name = 'Sublister'

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self.__tool_name, self.domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains:
            subdomains = set()
            command = f'cd /root/Desktop/TOOLs/Sublist3r/; python sublist3r.py -d {self.domain} | grep "Total Unique Subdomains Found" -A 999'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            skip_first_line = True
            for line in bash_outputs:
                if skip_first_line:
                    skip_first_line = False
                    continue
                subdomains.add(line.replace('\x1b[92m', '').replace('\x1b[0m\n', ''))
            cache_manager.save_result(subdomains)
        result = super().check_subdomains(subdomains)
        return result
