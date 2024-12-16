import os
from datetime import datetime
from tld import get_tld
from Helpers.CacheHelper import CacheHelper


class MassDns:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._massdns_out_of_scope_domains = os.environ.get("massdns_out_of_scope_domains")

    def get_subdomains(self, avoid_cache=False) -> set:
        out_of_scope = [x for x in self._massdns_out_of_scope_domains.split(';') if x]

        if any(oos in self._domain for oos in out_of_scope):
            print(f'{self._domain} out of scope massdns')
            return set()

        top_domain_res = get_tld(f"http://{self._domain}", as_object=True)
        if top_domain_res.fld != self._domain.replace('www.', ''):
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) is not a root domain')
            return set()

        cache_manager = CacheHelper(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if (not subdomains and not isinstance(subdomains, set)) or avoid_cache:
            if not os.path.exists(self._tool_result_dir):
                os.makedirs(self._tool_result_dir)

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} starts...')

            massdns_result_file = f"{self._tool_result_dir}/{self._domain}_raw.txt"
            subdomains = set()
            if not os.path.exists(massdns_result_file):
                command = f'cd /root/Desktop/TOOLs/massdns/; ' \
                          f'./scripts/subbrute.py {self._domain} lists/all.txt | ' \
                          f'./bin/massdns -r lists/resolvers.txt -t A -o S -w {massdns_result_file}'
                stream = os.popen(command)
                stream.read()

                if os.path.exists(massdns_result_file):
                    with open(massdns_result_file) as file:
                        for line in file:
                            subdomain = str(line.split(' ')[0]).strip('.').lower()
                            subdomain = subdomain.replace('*.', '')
                            subdomains.add(subdomain)

            os.remove(massdns_result_file)
            cache_manager.cache_result(subdomains)

        if len(subdomains) > 10000:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) '
                  f'{self._tool_name} failed! Found too many items.')
            return set()
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) '
              f'{self._tool_name} found {len(subdomains)} items')
        return subdomains

