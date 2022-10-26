import os
from datetime import datetime

from Managers.SubdomainChecker import SubdomainChecker
from Managers.Tools.Amass import Amass
from Managers.Tools.Dirb import Dirb
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.Tools.Nmap import Nmap
from Managers.Tools.SubBrute import SubBrute
from Managers.Tools.Sublister import Sublister
from Managers.ThreadManager import ThreadManager


class DomainFlowManager:
    def __init__(self, headers, single_url_man: SingleUrlFlowManager):
        self.download_path = os.environ.get('download_path')
        self.headers = headers
        self.single_url_man = single_url_man

    def check_domain(self, domain):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Sublister started...')

        sublister = Sublister(domain)
        sublister_subdomains = sublister.get_subdomains()

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Sublister found {len(sublister_subdomains)} items')
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Amass started...')
        # amass = Amass(domain)
        # amass_subdomains = amass.get_subdomains()
        amass_subdomains = set()

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Amass found {len(amass_subdomains)} items')

        all_subdomains = amass_subdomains.union(sublister_subdomains)

        nmap = Nmap(domain)
        nmap.check_ports(all_subdomains)

        subdomain_checker = SubdomainChecker(domain, self.headers, self.download_path)
        subdomain_urls = subdomain_checker.check_subdomains(all_subdomains)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager started...')

        thread_man = ThreadManager()
        thread_man.run_all(self.single_url_man.run, subdomain_urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager: FINISHED {len(subdomain_urls)} urls')
