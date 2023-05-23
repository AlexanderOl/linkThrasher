import json
import os
import re
import shutil
from datetime import datetime
from glob import glob
from subprocess import Popen, PIPE, STDOUT

from Common.ProcessKiller import ProcessKiller
from Managers.CacheManager import CacheManager


class Knock:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):

            res_dir = f'{self._tool_result_dir}/{self._domain}'

            command = f"echo '{self._domain}' | knockpy --silent --no-local --no-http -o {res_dir}"
            stream = os.popen(command)
            stream.read()

            subdomains = set()
            files = glob(f'{res_dir}/*')
            if len(files) == 0:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} nothing found')
            for file in files:
                f = open(file)
                data = json.load(f)
                for row in data:
                    if self._domain in row:
                        subdomains.add(row)
                f.close()

            shutil.rmtree(res_dir, ignore_errors=True)

            cache_manager.save_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains
