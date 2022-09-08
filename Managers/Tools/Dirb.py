import os
from Managers.CacheManager import CacheManager


class Dirb:
    def __init__(self, domain):
        self.cache_manager = CacheManager('Dirb', domain)

    def check_single_url(self, url):
        command = f"dirb {url} -r -f"
        stream = os.popen(command)
        bash_outputs = stream.readlines()

        if len(bash_outputs) == 0 and 'https' not in url:
            url = url.replace('http', 'https')
            self.check_subdomain_urls(url)
        filtered_output = list(filter(lambda o: 'CODE:200' in o or 'DIRECTORY:' in o, bash_outputs))
        print(f'Dirb {url} finished. Found {len(filtered_output)}')
        self.cache_manager.save_result(filtered_output)

