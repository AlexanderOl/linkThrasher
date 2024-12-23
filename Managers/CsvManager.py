import glob
import ipaddress
from csv import reader
from datetime import date

import inject

from Common.Logger import Logger
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Managers.DomainManager import DomainManager
from Managers.UrlListManager import UrlListManager


class CsvManager:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._target_files = f'Targets/*.csv'
        self._domains = set()
        self._urls = set()
        self._ips = set()
        self._cache_keys = str(date.today())
        self._logger = inject.instance(Logger)
        self._request_handler = inject.instance(RequestHandler)
        self._multiple_man = inject.instance(UrlListManager)
        self._domain_man = inject.instance(DomainManager)
        self._thread_manager = inject.instance(ThreadManager)

    def run(self):

        self.__parse_csv()

        print(f'FOUND DOMAINS: {", ".join(self._domains)}')
        print(f'FOUND URLS: {", ".join(self._urls)}')
        print(f'FOUND IPS: {", ".join(self._ips)}')

        for domain in self._domains:
            self._domain_man.check_domain(domain)

        for ip in self._ips:
            self._domain_man.check_ip(ip)

        if len(self._urls):
            self._multiple_man.run(self._urls)

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
                            and row[1].upper() in ['WILDCARD', 'URL', 'OTHER', 'CIDR', 'IP_ADDRESS', 'API']:
                        target = str(row[0])

                        if 'play.google.com' in target or 'apps.apple.com' in target:
                            continue

                        if row[1].upper() == 'IP_ADDRESS':
                            ips.add(target)
                        elif target.startswith('http'):
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

        self._thread_manager.run_all(self.__ping_domain, domains)
        self._thread_manager.run_all(self.__ping_url, urls)
        self._thread_manager.run_all(self.__ping_ip, ips)

        self._domains = list(sorted(self._domains, key=lambda s: s.count('.')))

        cache_man.cache_result({'urls': self._urls, 'domains': self._domains, 'ips': self._ips})

    def __ping_domain(self, domain):
        url = f'http://{domain}'
        response = self._request_handler.send_head_request(url, timeout=15)
        if response is not None:
            self._domains.add(domain)
            return

        url = f'https://{domain}'
        response = self._request_handler.send_head_request(url, timeout=15)
        if response is not None:
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
