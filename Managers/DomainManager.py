import os
import validators
from datetime import datetime
from urllib3 import exceptions, disable_warnings

from Common.RequestHandler import RequestHandler
from Common.ThreadBucket import ThreadBucket
from Dal.MysqlRepository import MysqlRepository
from Managers.SingleUrlManager import SingleUrlManager
from Helpers.SubdomainChecker import SubdomainChecker
from Common.ThreadManager import ThreadManager
from Tools.Amass import Amass
from Tools.Dnsx import Dnsx
from Tools.EyeWitness import EyeWitness
from Tools.Knock import Knock
from Tools.MassDns import MassDns
from Tools.Nmap import Nmap
from Tools.Nuclei import Nuclei
from Tools.SubFinder import SubFinder


class DomainManager:
    def __init__(self, headers):
        self._download_path = os.environ.get('download_path')
        self._headers = headers
        self._check_mode = os.environ.get('check_mode')
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._targets_domains_file = 'Targets/domains.txt'
        self._tool_name = self.__class__.__name__
        disable_warnings(exceptions.InsecureRequestWarning)

    def check_ip(self, ip):
        ips = set()
        ips.add(ip)

        subdomain_checker = SubdomainChecker(ip, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(ips)

        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        mysql_repo = MysqlRepository()
        db_urls = mysql_repo.get_tracked_urls(ip)
        filtered_urls = list([dto for dto in start_urls_dtos if all(db_sub != dto.url for db_sub in db_urls)])

        if len(filtered_urls) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({ip}) No live urls found at ip')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({ip}) Found {len(start_urls_dtos)} start urls at ip')

        nmap = Nmap(ip, self._headers)
        nmap_get_dtos = nmap.check_ports(filtered_urls)
        filtered_urls += nmap_get_dtos

        eyewitness = EyeWitness(ip, self._headers)
        eyewitness.visit_dtos(filtered_urls)

        nuclei = Nuclei(ip, self._headers)
        nuclei.check_multiple_uls(filtered_urls)

        single_url_man = SingleUrlManager(self._headers)
        thread_man = ThreadManager()
        thread_man.run_all(single_url_man.do_run, filtered_urls, f' ({ip})')

        db_urls.update(set([dto.url for dto in filtered_urls]))
        mysql_repo.save_tracker_urls_result(ip, db_urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ip ({ip})')

    def check_multiple_domains(self):

        if os.path.exists(self._targets_domains_file):
            domains = list(set(line.strip() for line in open(self._targets_domains_file)))

            thread_man = ThreadBucket()
            thread_man.run_all(self.__check_batch_domains, domains, debug_msg=self._tool_name)
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._targets_domains_file} is missing')

    def __check_batch_domains(self, domain):
        request_helper = RequestHandler(cookies='', headers=self._headers)
        print(f'Checking {domain} domain...')
        resp = request_helper.send_head_request(f'http://{domain}')
        if resp is None:
            return
        print(f'Domain {domain} init status - {resp.status_code}')
        self.check_domain(domain)
        print(f'Check {domain} finished!')

    def check_domain(self, domain):
        domain = domain.lower().replace('www.', '')
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
            # massdns_subdomains = massdns.get_subdomains()

        all_subdomains = amass_subdomains \
            .union(knock_subdomains) \
            .union(subfinder_subdomains) \
            .union(massdns_subdomains)

        dnsx = Dnsx(domain)
        dnsx.get_dnsx_report(all_subdomains)

        if domain not in all_subdomains:
            all_subdomains.add(domain)

        mysql_repo = MysqlRepository()
        db_subdomains = mysql_repo.get_tracked_subdomains(domain)
        filtered_domains = set([sub for sub in all_subdomains if all(db_sub != sub for db_sub in db_subdomains)])

        subdomain_checker = SubdomainChecker(domain, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(filtered_domains)

        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        db_subdomains.update(filtered_domains)
        if len(start_urls_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live domains found')
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) Found {len(start_urls_dtos)} start urls')

            nmap = Nmap(domain, self._headers)
            nmap_get_dtos = nmap.check_ports(start_urls_dtos)
            start_urls_dtos += nmap_get_dtos

            db_urls = mysql_repo.get_tracked_urls(domain)
            filtered_urls = list([dto for dto in start_urls_dtos if all(db_url != dto.url for db_url in db_urls)])

            if len(filtered_urls) == 0:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live urls found')
            else:
                eyewitness = EyeWitness(domain, self._headers)
                eyewitness.visit_dtos(filtered_urls)

                nuclei = Nuclei(domain, self._headers)
                nuclei.check_multiple_uls(filtered_urls)

                single_url_man = SingleUrlManager(self._headers)
                thread_man = ThreadManager()
                thread_man.run_all(single_url_man.do_run, filtered_urls)

                db_urls.update(set([dto.url for dto in filtered_urls]))
                mysql_repo.save_tracker_urls_result(domain, db_urls)

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ({domain})')

        mysql_repo.save_tracker_domains_result(domain, db_subdomains)
