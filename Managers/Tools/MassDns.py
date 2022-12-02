import os
from datetime import datetime

from Managers.CacheManager import CacheManager


class MassDns:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain
        self.__tool_result_dir = f'{os.environ.get("app_result_path")}{self.__tool_name}'

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):

            if not os.path.exists(self.__tool_result_dir):
                os.makedirs(self.__tool_result_dir)

            massdns_result_file = f"{self.__tool_result_dir}/{self.__domain}_raw.txt"
            command = f'cd /root/Desktop/TOOLs/massdns/; ' \
                      f'./scripts/subbrute.py lists/all.txt {self.__domain} | ' \
                      f'./bin/massdns -r lists/resolvers.txt -t A -o S -w {massdns_result_file}'
            stream = os.popen(command)
            stream.read()

            subdomains = set()
            if os.path.exists(massdns_result_file):
                with open(massdns_result_file) as file:
                    for line in file:
                        subdomain = str(line.split(' ')[0]).strip('.').lower()
                        subdomains.add(subdomain)

            os.remove(massdns_result_file)
            cache_manager.save_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(subdomains)} items')
        return subdomains

