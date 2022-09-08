import os
import pickle
import urllib

import requests

from datetime import datetime

from Managers.BaseSubdomainManager import BaseSubdomainManager
from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager


class Amass(BaseSubdomainManager):
    def __init__(self, domain, headers, download_path):
        super().__init__(domain, headers, download_path)
        self.__domain = domain
        self.__tool_name = 'Amass'

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains:
            subdomains = set()
            command = f'amass enum -d {self.__domain}'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            for line in bash_outputs:
                if self.__domain in line:
                    subdomains.add(line.replace('\n', ''))
            cache_manager.save_result(subdomains)
        result = super().check_subdomains(subdomains)
        return result
