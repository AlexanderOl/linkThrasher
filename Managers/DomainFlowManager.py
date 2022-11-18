import os
from datetime import datetime

from Managers.SubdomainChecker import SubdomainChecker
from Managers.Tools.Amass import Amass
from Managers.Tools.Dirb import Dirb
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.Tools.EyeWitness import EyeWitness
from Managers.Tools.Httpx import Httpx
from Managers.Tools.Nmap import Nmap
from Managers.Tools.MassDns import MassDns
from Managers.Tools.SubFinder import SubFinder
from Managers.Tools.Sublister import Sublister
from Managers.ThreadManager import ThreadManager


class DomainFlowManager:
    def __init__(self, headers, single_url_man: SingleUrlFlowManager):
        self.download_path = os.environ.get('download_path')
        self.headers = headers
        self.single_url_man = single_url_man

    def check_domain(self, domain):

        sublister = Sublister(domain)
        sublister_subdomains = sublister.get_subdomains()
        # sublister_subdomains = set()

        amass = Amass(domain)
        amass_subdomains = amass.get_subdomains()
        # amass_subdomains = set()

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains()

        massdns = MassDns(domain)
        massdns_subdomains = massdns.get_subdomains()

        all_subdomains = amass_subdomains\
            .union(sublister_subdomains)\
            .union(subfinder_subdomains)\
            .union(massdns_subdomains)

        httpx = Httpx(domain)
        live_urls = httpx.check_subdomains(all_subdomains)

        eyewitness = EyeWitness(domain)
        eyewitness.visit_urls(live_urls)

        # nmap = Nmap(domain)
        # nmap.check_ports(all_subdomains)

        thread_man = ThreadManager()
        thread_man.run_all(self.single_url_man.run, live_urls)

