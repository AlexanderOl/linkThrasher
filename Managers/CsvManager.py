import glob
import ipaddress
import os
from csv import reader
from datetime import date
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Managers.DomainManager import DomainManager
from Managers.UrlListManager import UrlListManager


class CsvManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._target_files = f'Targets/*.csv'
        self._request_handler = RequestHandler(headers=headers)
        self._domains = set()
        self._urls = set()
        self._ips = set()
        self._cache_keys = str(date.today())

    def run(self):

        self.__parse_csv()

        print(f'FOUND {", ".join(self._domains)} DOMAINS')
        print(f'FOUND {", ".join(self._urls)} URLS')
        print(f'FOUND {", ".join(self._ips)} IPs')

        domain_man = DomainManager(self._headers)
        for domain in self._domains:
            domain_man.check_domain(domain)

        for ip in self._urls:
            domain_man.check_ip(ip)

        multiple_man = UrlListManager(self._headers)
        multiple_man.run(self._urls)

    def __parse_csv(self):

        cache_man = CacheHelper(self._tool_name, self._cache_keys)
        csv = cache_man.get_saved_result()
        if csv:
            self._urls = csv['urls']
            self._domains = csv['domains']
            self._ips = csv['ips']
            return

        domains = set()
        ips = set()
        urls = set()

        files = glob.glob(self._target_files)
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
                            ips_to_add = set([str(ip) for ip in ipaddress.IPv4Network(target, False)])
                            ips.update(ips_to_add)
                        elif ' ' not in target:
                            domains.add(target.replace('*', ''))
                    else:
                        print(f"NotEligible/OOS: {', '.join(row)}")

        thread_man = ThreadManager()
        thread_man.run_all(self.__ping_domain, domains)
        thread_man.run_all(self.__ping_url, urls)
        thread_man.run_all(self.__ping_ip, ips)

        cache_man.save_result({'urls': self._urls, 'domains': self._domains, 'ips': self._ips})

    def __ping_domain(self, domain):
        url = f'http://{domain}'
        response = self._request_handler.send_head_request(url, timeout=10)
        if response:
            self._domains.add(domain)

    def __ping_url(self, url):
        response = self._request_handler.send_head_request(url)
        if response:
            self._urls.add(url)

    def __ping_ip(self, ip):
        url = f'http://{ip}'
        response = self._request_handler.send_head_request(url, timeout=3)
        if response:
            self._ips.add(ip)
