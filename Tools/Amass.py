import re
import ipaddress
from datetime import datetime

from Common.ProcessKiller import ProcessKiller
from Helpers.CacheManager import CacheManager


class Amass:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def get_subdomains(self) -> set:
        cache_manager = CacheManager(self._tool_name, self._domain)
        subdomains = cache_manager.get_saved_result()
        if not subdomains and not isinstance(subdomains, set):

            cmd_arr = ['amass', 'enum', '-d', self._domain, '-r', '8.8.8.8,1.1.1.1']
            pk = ProcessKiller()
            bash_outputs = pk.run_temp_process(cmd_arr, self._domain, timeout=1200)

            subdomains = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)

                if 'a_record' in encoded_line:
                    subdomain = encoded_line.split('a_record')[1].split(' ')[2]
                    subdomains.add(subdomain)

                elif 'aaaa_record' in encoded_line:
                    subdomain = f"[{encoded_line.split('aaaa_record')[1].split(' ')[2]}]"
                    subdomains.add(subdomain)

                elif 'contains' in encoded_line and not encoded_line.startswith('10'):
                    target = encoded_line.split(' ')[0]
                    if '::' in target:
                        if int(target.split('/')[1]) > 96:
                            subdomains.update(set([str(ip) for ip in ipaddress.IPv6Network(target)]))
                    else:
                        if int(target.split('/')[1]) > 24:
                            subdomains.update(set([str(ip) for ip in ipaddress.IPv4Network(target)]))
                if self._domain in encoded_line:
                    subdomain = encoded_line.split(' ')[0].replace('\n', '')
                    subdomains.add(subdomain)
            cache_manager.save_result(subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(subdomains)} items')
        return subdomains
