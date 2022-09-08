import os
from datetime import datetime

from Managers.Tools.Amass import Amass
from Managers.Tools.Dirb import Dirb
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.Tools.SubBrute import SubBrute
from Managers.Tools.Sublister import Sublister
from Managers.ThreadManager import ThreadManager


class DomainFlowManager:
    def __init__(self, headers, single_url_man: SingleUrlFlowManager):
        self.download_path = os.environ.get('__download_path')
        self.headers = headers
        self.single_url_man = single_url_man

    def check_domain(self, domain):

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Sublister started...')

        sublister = Sublister(domain, self.headers, self.download_path)
        sublister_subdomain_urls = sublister.get_subdomains()

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Sublister found {len(sublister_subdomain_urls)} items')
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Amass started...')
        amass = Amass(domain, self.headers, self.download_path)
        amass_subdomain_urls = amass.get_subdomains()

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Amass found {len(amass_subdomain_urls)} items')

        subdomain_urls = amass_subdomain_urls.union(sublister_subdomain_urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb: started...')

        dirb = Dirb(domain)
        thread_man = ThreadManager()
        thread_man.run_all(dirb.check_single_url, subdomain_urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Dirb: FINISHED {len(subdomain_urls)} urls')
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager started...')

        thread_man.run_all(self.single_url_man.run, subdomain_urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager: FINISHED {len(subdomain_urls)} urls')
