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
        urls = set()

        files = glob.glob(f'Targets/*.csv')
        for file in files:
            with open(file, 'r') as read_obj:

                csv_reader = reader(read_obj)
                for row in csv_reader:

                    if len(row) >= 5:
                        if row[1].upper() in ['WILDCARD', 'URL', 'OTHER'] and row[3] == 'true' and row[4] == 'true':
                            if row[0].startswith('http'):
                                urls.add(row[0])
                            elif '*.' in row[0]:
                                domains.add(row[0].replace('*.', ''))
                            elif row[0].startswith('www.'):
                                domains.add(row[0].replace('www.', ''))
                            else:
                                domains.add(row[0])
                        elif row[1].upper() == 'CIDR' and row[3] == 'true' and row[4] == 'true':
                            ips_str = str(row[0])
                            if '/' in ips_str:
                                ips = [str(ip) for ip in ipaddress.IPv4Network(ips_str)]


                    else:
                        print(f"NotEligible/OOS: {', '.join(row)}")

        print(f'FOUND {", ".join(domains)} DOMAINS and {", ".join(urls)} URLS')

        if len(domains) > 0:
            domain_man = DomainFlowManager(self._headers)
            for domain in domains:
                domain_man.check_domain(domain)

        if len(urls) > 0:
            multiple_man = MultipleUrlFlowManager(self._headers)
            multiple_man.run(urls)
