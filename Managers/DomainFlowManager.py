import os
from datetime import datetime, date
import urllib3
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.SubdomainChecker import SubdomainChecker
from Managers.ThreadManager import ThreadManager
from Tools.Amass import Amass
from Tools.EyeWitness import EyeWitness
from Tools.MassDns import MassDns
from Tools.Nmap import Nmap
from Tools.Nuclei import Nuclei
from Tools.SubFinder import SubFinder


class DomainFlowManager:
    def __init__(self, headers):
        self._download_path = os.environ.get('download_path')
        self._headers = headers
        self._check_mode = os.environ.get('check_mode')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def check_domain(self, domain):
        amass = Amass(domain)
        amass_subdomains = amass.get_subdomains()
        # amass_subdomains = set()

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains()
        # subfinder_subdomains = set()

        massdns = MassDns(domain)
        massdns_subdomains = massdns.get_subdomains()
        # massdns_subdomains = set()

        all_subdomains = amass_subdomains \
            .union(subfinder_subdomains) \
            .union(massdns_subdomains)

        subdomain_checker = SubdomainChecker(domain, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(all_subdomains)
        if len(start_urls_dtos) == 0:
            print('No live subdomains found')
            return
        else:
            print(f'Found {len(start_urls_dtos)} start urls')

        eyewitness = EyeWitness(domain, self._headers)
        eyewitness.visit_dtos(start_urls_dtos)

        nuclei = Nuclei(domain, self._headers)
        nuclei.check_multiple_uls(start_urls_dtos)

        nmap = Nmap(domain)
        nmap.check_ports(start_urls_dtos)

        single_url_man = SingleUrlFlowManager(self._headers)
        thread_man = ThreadManager()
        thread_man.run_all(single_url_man.run, start_urls_dtos)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ({domain})')
