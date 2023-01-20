import os
import re
from datetime import datetime

from Managers.CacheManager import CacheManager


class Amass:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):
            subdomains = set()
            command = f'amass enum -d {self._domain}'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                if self._domain in encoded_line:
                    subdomains.add(encoded_line.replace('\n', ''))
            cache_manager.save_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains
