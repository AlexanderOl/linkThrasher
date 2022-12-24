import os
import pathlib
from datetime import datetime

from Managers.CacheManager import CacheManager


class LinkFinder:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def search_urls_in_js(self, script_urls: set) -> set:

        tool_directory = f"Results/{self.__tool_name}/{self.__domain}"
        if not os.path.exists(tool_directory):
            os.makedirs(tool_directory)
        output_filepath = f'{tool_directory}/output.html'
        if not os.path.exists(output_filepath):
            domain_tool_directory_path = os.path.join(pathlib.Path().resolve(), tool_directory)
            for url in script_urls:
                command = f'cd {domain_tool_directory_path}; wget {url} -q'
                stream = os.popen(command)
                stream.read()

            command = f'cd /root/Desktop/TOOLs/LinkFinder; ' \
                      f'python linkfinder.py -i "{domain_tool_directory_path}/*" -o "{domain_tool_directory_path}/output.html" '
            stream = os.popen(command)
            stream.read()

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} finished')
