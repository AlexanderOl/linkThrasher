import os
import pathlib
from datetime import datetime

from Models.Constants import URL_IGNORE_EXT_REGEX


class LinkFinder:
    def __init__(self, domain, start_url):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._start_url = start_url
        self._black_list = ["application/", "text/", "image/", "mm/dd/yyyy", "yyyy/mm/dd", "dd/m/yyyy", "mm/d/yyyy",
                            "request/", "dojo/", "audio/", "video/", "font/", "/x-icon"]

    def search_urls_in_js(self, script_urls: set) -> set:

        result = set()
        if len(script_urls) == 0:
            return result

        tool_directory = f"{self._tool_result_dir}/{self._domain}"
        if not os.path.exists(tool_directory):
            os.makedirs(tool_directory)

        domain_tool_directory_path = os.path.join(pathlib.Path().resolve(), tool_directory)
        for url in script_urls:
            command = f'cd {domain_tool_directory_path}; wget {url} -q --timeout=20 --tries=2'
            stream = os.popen(command)
            stream.read()

        command = f'cd /root/Desktop/TOOLs/LinkFinder; ' \
                  f'python linkfinder.py -i "{domain_tool_directory_path}/*" -o cli'
        stream = os.popen(command)
        bash_outputs = stream.readlines()

        for found in set([x.lower() for x in bash_outputs]):
            if 'linkfinder.py' in found:
                break
            if URL_IGNORE_EXT_REGEX.search(found) or 'mailto:' in found:
                continue
            if found.startswith('./'):
                found = found[2:]
            if found.endswith('\n'):
                found = found[:-2]
            if not any(word in found for word in self._black_list):
                if found.startswith('http'):
                    if self._domain in found:
                        result.add(found)
                    else:
                        continue
                elif not found:
                    continue
                elif found[0] == '/':
                    result.add(f'{self._start_url.rstrip("/")}/{found[1:]}')
                else:
                    result.add(f'{self._start_url}/{found}')

        # shutil.rmtree(tool_directory, ignore_errors=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} finished')
        return result
