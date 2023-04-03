import os
from datetime import datetime

from Managers.CacheManager import CacheManager


class MassDns:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._massdns_out_of_scope_domains = os.environ.get("massdns_out_of_scope_domains")

    def get_subdomains(self) -> set:
        out_of_scope = [x for x in self._massdns_out_of_scope_domains.split(';') if x]

        if any(oos in self._domain for oos in out_of_scope):
            print(f'{self._domain} out of scope massdns')
            return set()
        cache_manager = CacheManager(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):
            if not os.path.exists(self._tool_result_dir):
                os.makedirs(self._tool_result_dir)

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} starts...')

            massdns_result_file = f"{self._tool_result_dir}/{self._domain}_raw.txt"
            command = f'cd /root/Desktop/TOOLs/massdns/; ' \
                      f'./scripts/subbrute.py lists/all-1m.txt {self._domain} | ' \
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

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains

