import os
from datetime import datetime

import urllib3

from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.SubdomainChecker import SubdomainChecker
from Managers.ThreadManager import ThreadManager
from Managers.Tools.Amass import Amass
from Managers.Tools.EyeWitness import EyeWitness
from Managers.Tools.MassDns import MassDns
from Managers.Tools.SubFinder import SubFinder


class DomainFlowManager:
    def __init__(self, headers):
        self.download_path = os.environ.get('download_path')
        self.headers = headers
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def check_domain(self, domain):
        print(f'Checking {domain} domain')

        # sublister = Sublister(domain)
        # sublister_subdomains = sublister.get_subdomains()
        sublister_subdomains = set()

        amass = Amass(domain)
        amass_subdomains = amass.get_subdomains()
        # amass_subdomains = set()

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains()
        # subfinder_subdomains = set()

        massdns = MassDns(domain)
        massdns_subdomains = massdns.get_subdomains()
        # massdns_subdomains = set()

        all_subdomains = amass_subdomains\
            .union(sublister_subdomains)\
            .union(subfinder_subdomains)\
            .union(massdns_subdomains)

        subdomain_checker = SubdomainChecker(domain, self.headers, self.download_path)
        start_urls_dtos = subdomain_checker.check_all_subdomains(all_subdomains)
        if len(start_urls_dtos) == 0:
            print('No live subdomains found')
            return
        else:
            print(f'Found {len(start_urls_dtos)} start urls')

        live_urls = set(line.url for line in start_urls_dtos)

        eyewitness = EyeWitness(domain)
        eyewitness.visit_urls(live_urls)

        # nmap = Nmap(domain)
        # nmap.check_ports(all_subdomains)
        single_url_man = SingleUrlFlowManager(self.headers)
        thread_man = ThreadManager()
        thread_man.run_all(single_url_man.run, start_urls_dtos)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ({domain})')

