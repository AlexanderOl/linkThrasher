import re
from datetime import datetime

from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper


class Amass:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def get_subdomains(self, avoid_cache=False) -> set:
        cache_manager = CacheHelper(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if (not subdomains and not isinstance(subdomains, set)) or avoid_cache:

            cmd_arr = ['amass', 'enum', '-d', self._domain, '-r', '8.8.8.8,1.1.1.1']
            pk = ProcessHandler()
            bash_outputs = pk.run_temp_process(cmd_arr, self._domain, timeout=1200)

            subdomains = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)

                split = encoded_line.split(' ')
                for item in split:
                    if self._domain in item:
                        subdomains.add(item)

            cache_manager.cache_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains
