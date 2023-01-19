import os
import pathlib
from datetime import datetime

from Managers.CacheManager import CacheManager


class Httpx:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain

    def check_subdomains(self, all_subdomains) -> set:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        live_urls = cache_manager.get_saved_result()
        if not live_urls:
            live_urls = set()
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
                      f'go run httpx.go -silent -l {subdomains_filepath}'

            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if self.__domain in line:
                    live_urls.add(line.replace('\n', ''))
            live_urls = sorted(live_urls)
            os.remove(txt_filepath)
            cache_manager.save_result(live_urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(live_urls)} items')
        return live_urls
