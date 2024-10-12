import re
from datetime import datetime

import inject

from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper


class Amass:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._logger = inject.instance(Logger)
        self._process_handler = inject.instance(ProcessHandler)

    def get_subdomains(self, domain: str) -> set:
        cache_manager = CacheHelper(self._tool_name, domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):

            cmd_arr = ['amass', 'enum', '-d', domain, '-r', '8.8.8.8,1.1.1.1']
            bash_outputs = self._process_handler.run_temp_process(cmd_arr, domain, timeout=1200)

            subdomains = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)

                split = encoded_line.split(' ')
                for item in split:
                    if item.endswith(domain):
                        subdomains.add(item)
                    elif domain in item:
                        self._logger.log_warn(f'{item} amass found not added')

            if len(subdomains) == 0:
                subdomains.add(domain)

            cache_manager.cache_result(subdomains)

        self._logger.log_info(f'({domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains
