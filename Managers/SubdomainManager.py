import os
from datetime import datetime

import requests

from Managers.CacheManager import CacheManager


class SubdomainManager:
    def __init__(self):
        self.__checked_redirect_url_parts = {}
        self.target_file = f'Targets/domains.txt'

    def get_subdomains(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SubdomainManager started...')

        subdomains_dict = {}

        if os.path.exists(self.target_file):
            with open(self.target_file) as file:
                for domain in file:
                    cache_manager = CacheManager('SubdomainManagerResult', domain)
                    subdomains = cache_manager.get_saved_result()
                    if subdomains is None:
                        subdomains = set()
                        command = f'cd /root/Desktop/TOOLs/Sublist3r/; python sublist3r.py -d {domain} | grep "Total Unique Subdomains Found" -A 999'
                        stream = os.popen(command)
                        bash_outputs = stream.readlines()
                        skip_first_line = True
                        for line in bash_outputs:
                            if skip_first_line:
                                skip_first_line = False
                                continue
                            subdomains.add(line.replace('\x1b[92m', '').replace('\x1b[0m\n', ''))
                        cache_manager.save_result(subdomains)
                    subdomains_dict[domain] = subdomains
        checked_domains = self.__check_subdomains(subdomains_dict)
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SubdomainManager found {len(subdomains_dict)} items')


    def __check_subdomains(self, subdomains_dict):
        checked_subdomains = {}
        for domain in subdomains_dict:
            subdomains = set()
            self.__checked_redirect_url_parts[domain]=set()
            for subdomain in subdomains_dict[domain]:
                url = f'http://{subdomain}/'
                try:
                    response = requests.get(url, timeout=3)
                    if response.status_code == 200:
                        without_url = response.url.replace(url, '')
                        if without_url not in self.__checked_redirect_url_parts[domain]:
                            self.__checked_redirect_url_parts[domain].add(without_url)
                            subdomains.add(response.url)
                    elif 300 <= response.status_code > 400:
                        print(f'response.status_code-{response.status_code}')
                        print(url)
                except Exception as inst:
                    print(inst)
                    continue
            checked_subdomains[domain] = subdomains
        return checked_subdomains
