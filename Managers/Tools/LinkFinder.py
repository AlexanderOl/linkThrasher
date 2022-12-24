import os
import re
import pathlib
import shutil
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO


class LinkFinder:
    def __init__(self, domain, start_url):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._start_url = start_url
        self._black_list = ["application/", "text/", "mm/dd/yyyy"]
        self._url_ignore_ext_regex = re.compile(
            '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.pdf$|\.ashx$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
            '|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.js$')

    def search_urls_in_js(self, script_urls: set) -> set:

        result = set()
        if len(script_urls) == 0:
            result

        tool_directory = f"Results/{self._tool_name}/{self._domain}"
        if not os.path.exists(tool_directory):
            os.makedirs(tool_directory)

        domain_tool_directory_path = os.path.join(pathlib.Path().resolve(), tool_directory)
        for url in script_urls:
            command = f'cd {domain_tool_directory_path}; wget {url} -q'
            stream = os.popen(command)
            stream.read()

        command = f'cd /root/Desktop/TOOLs/LinkFinder; ' \
                  f'python linkfinder.py -i "{domain_tool_directory_path}/*" -o cli'
        stream = os.popen(command)
        bash_outputs = stream.readlines()

        for found in set([x.lower() for x in bash_outputs]):
            if self._url_ignore_ext_regex.search(found):
                continue
            if found.endswith('\n'):
                found = found[:-1]
            if not any(word in found for word in self._black_list):
                if found.startswith('http') and self._domain in found:
                    result.add(found)
                elif found[0] == '/':
                    result.add(f'{self._start_url}{found[1:]}')
                else:
                    result.add(f'{self._start_url}{found}')

        shutil.rmtree(tool_directory, ignore_errors=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} finished')
        return result
