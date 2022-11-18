import os
import pathlib
from datetime import datetime

from Managers.CacheManager import CacheManager


class Httpx:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def check_subdomains(self, all_subdomains) -> set:
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: {self.__tool_name} started...')

        cache_manager = CacheManager(self.__tool_name, self.__domain)
        checked_subdomains = cache_manager.get_saved_result()
        if not checked_subdomains:
            checked_subdomains = set()
            httpx_directory = f"Results/{self.__tool_name}"
            if not os.path.exists(httpx_directory):
                os.makedirs(httpx_directory)
            txt_filepath = f"{httpx_directory}/{self.__domain}_raw.txt"
            txt_file = open(txt_filepath, 'a')
            for subdomain in all_subdomains:
                txt_file.write("%s\n" % str(subdomain))
            txt_file.close()

            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
            command = f'cd /root/Desktop/TOOLs/httpx/cmd/httpx/; ' \
                      f'cat {subdomains_filepath} | ' \
                      f'go run httpx.go -silent'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if self.__domain in line:
                    checked_subdomains.add(line.replace('\n', ''))

            os.remove(txt_filepath)
            cache_manager.save_result(checked_subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: {self.__tool_name} found {len(checked_subdomains)} items')
        return checked_subdomains
