import os
import validators
from datetime import datetime
from urllib3 import exceptions, disable_warnings
from Managers.SingleUrlManager import SingleUrlManager
from Helpers.SubdomainChecker import SubdomainChecker
from Common.ThreadManager import ThreadManager
from Tools.Amass import Amass
from Tools.EyeWitness import EyeWitness
from Tools.Knock import Knock
from Tools.MassDns import MassDns
from Tools.Nmap import Nmap
from Tools.Nuclei import Nuclei
from Tools.SubFinder import SubFinder
from Tools.Trufflehog import Trufflehog


class DomainManager:
    def __init__(self, headers):
        self._download_path = os.environ.get('download_path')
        self._headers = headers
        self._check_mode = os.environ.get('check_mode')
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._targets_domains_file = 'Targets/domains.txt'
        disable_warnings(exceptions.InsecureRequestWarning)

    def check_ip(self, ip):
        ips = set()
        ips.add(ip)

        subdomain_checker = SubdomainChecker(ip, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(ips)

        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        if len(start_urls_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({ip}) No live urls found at ip')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({ip}) Found {len(start_urls_dtos)} start urls at ip')

        nmap = Nmap(ip, self._headers)
        nmap_get_dtos = nmap.check_ports(start_urls_dtos)
        start_urls_dtos += nmap_get_dtos

        eyewitness = EyeWitness(ip, self._headers)
        eyewitness.visit_dtos(start_urls_dtos)

        nuclei = Nuclei(ip, self._headers)
        nuclei.check_multiple_uls(start_urls_dtos)

        single_url_man = SingleUrlManager(self._headers)
        thread_man = ThreadManager()
        thread_man.run_all(single_url_man.do_run, start_urls_dtos)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ip ({ip})')

    def check_multiple_domains(self):

        if os.path.exists(self._targets_domains_file):
            domains = list(set(line.strip() for line in open(self._targets_domains_file)))

            counter = len(domains)
            for domain in domains:
                print(f'Checking {domain} domain. Counter: {counter}')
                self.check_domain(domain)
                counter -= 1
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._targets_domains_file} is missing')

    def check_domain(self, domain):

        if not validators.domain(domain):
            print(f'{domain} is not a domain')
            return
        amass = Amass(domain)
        amass_subdomains = amass.get_subdomains()

        knock = Knock(domain)
        knock_subdomains = knock.get_subdomains()

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains()

        massdns_subdomains = set()
        if self._check_mode != 'DL':
            massdns = MassDns(domain)
            massdns_subdomains = massdns.get_subdomains()

        all_subdomains = amass_subdomains \
            .union(knock_subdomains) \
            .union(subfinder_subdomains) \
            .union(massdns_subdomains)

        subdomain_checker = SubdomainChecker(domain, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(all_subdomains)

        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        if len(start_urls_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live urls found')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) Found {len(start_urls_dtos)} start urls')

        nmap = Nmap(domain, self._headers)
        nmap_get_dtos = nmap.check_ports(start_urls_dtos)
        start_urls_dtos += nmap_get_dtos

        eyewitness = EyeWitness(domain, self._headers)
        eyewitness.visit_dtos(start_urls_dtos)

        nuclei = Nuclei(domain, self._headers)
        nuclei.check_multiple_uls(start_urls_dtos)

        single_url_man = SingleUrlManager(self._headers)
        thread_man = ThreadManager()
        thread_man.run_all(single_url_man.do_run, start_urls_dtos)

        th = Trufflehog(domain)
        th.check_secrets()

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ({domain})')
