import glob
import ipaddress
import os

from csv import reader
from Managers.DomainFlowManager import DomainFlowManager
from Managers.MultipleUrlFlowManager import MultipleUrlFlowManager


class CsvManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'

    def run(self):

        domains = set()
        ips = set()
        urls = set()

        files = glob.glob(f'Targets/*.csv')
        for file in files:
            with open(file, 'r') as read_obj:

                csv_reader = reader(read_obj)
                for row in csv_reader:

                    if len(row) >= 5 and row[3] == 'true' and row[4] == 'true' \
                            and row[1].upper() in ['WILDCARD', 'URL', 'OTHER', 'CIDR']:
                        target = str(row[0])
                        if target.startswith('http'):
                            urls.add(target)
                        elif '*' in target and '/' in target and row[1].upper() == 'WILDCARD':
                            urls.add(f"https://{target.replace('*', '')}")
                        elif '*.' in target:
                            domains.add(target.replace('*.', '').replace('*', ''))
                        elif target.startswith('www.'):
                            domains.add(target.replace('www.', ''))
                        elif '/' in str(target):
                            ips.update(set([str(ip) for ip in ipaddress.IPv4Network(target)]))
                        elif ' ' not in target:
                            domains.add(target.replace('*', ''))
                    else:
                        print(f"NotEligible/OOS: {', '.join(row)}")

        print(f'FOUND {", ".join(domains)} DOMAINS')
        print(f'FOUND {", ".join(urls)} URLS')
        print(f'FOUND {", ".join(ips)} IPs')

        if len(domains) > 0:
            domain_man = DomainFlowManager(self._headers)
            for domain in domains:
                domain_man.check_domain(domain)

        if len(ips) > 0:
            domain_man = DomainFlowManager(self._headers)
            for ip in ips:
                domain_man.check_ip(ip)

        if len(urls) > 0:
            multiple_man = MultipleUrlFlowManager(self._headers)
            multiple_man.run(urls)
