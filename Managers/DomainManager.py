import os
import validators
from urllib3 import exceptions, disable_warnings
from datetime import datetime
from Common.RequestHandler import RequestHandler
from Common.ThreadBucket import ThreadBucket
from Common.ThreadManager import ThreadManager
from Dal.MysqlRepository import MysqlRepository
from Helpers.CookieHelper import CookieHelper
from Helpers.SubdomainChecker import SubdomainChecker
from Managers.SingleUrlManager import SingleUrlManager
from Tools.Amass import Amass
from Tools.EyeWitness import EyeWitness
from Tools.Knock import Knock
from Tools.MassDns import MassDns
from Tools.Nmap import Nmap
from Tools.Nuclei import Nuclei
from Tools.SubFinder import SubFinder
from Tools.Waymore import Waymore


class DomainManager:
    def __init__(self, headers):
        self._download_path = os.environ.get('download_path')
        self._check_mode = os.environ.get('check_mode')
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._domain_batch_size = int(os.environ.get("domain_batch_size"))
        self._severity = int(os.environ.get("severity"))
        self._targets_domains_file = 'Targets/domains.txt'
        self._targets_domains_part_file = 'Targets/domains_part.txt'
        self._tool_name = self.__class__.__name__
        self._headers = headers
        disable_warnings(exceptions.InsecureRequestWarning)
        self._request_handler = RequestHandler(headers=headers)

    def check_ip(self, ip):
        ips = set()
        ips.add(ip)

        subdomain_checker = SubdomainChecker(ip, self._request_handler)
        start_urls_dtos = subdomain_checker.check_all_subdomains(ips)

        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        if len(start_urls_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({ip}) No live urls found at ip')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({ip}) Found {len(start_urls_dtos)} start urls at ip')

        nmap = Nmap(ip, self._request_handler)
        nmap_get_dtos = nmap.check_ports(start_urls_dtos)
        start_urls_dtos += nmap_get_dtos

        eyewitness = EyeWitness(ip, self._request_handler)
        eyewitness.visit_dtos(start_urls_dtos)

        nuclei = Nuclei(ip, self._headers)
        nuclei.check_multiple_uls(start_urls_dtos)

        single_url_man = SingleUrlManager(self._headers)
        thread_man = ThreadManager()
        thread_man.run_all(single_url_man.do_run, start_urls_dtos, f' ({ip})')

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ip ({ip})')

    def check_multiple_domains(self):

        if self._domain_batch_size == 0:
            with open(self._targets_domains_file) as infile:
                for domain in infile:
                    self.__check_batch_domains(domain.strip())
            infile.close()
            return
        while True:
            last_domain = self.__process_targets()
            if not last_domain:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: DL finished...')
                break

            if os.path.exists(self._targets_domains_file):
                target_domains = []
                can_add_targets = False
                with open(self._targets_domains_file) as infile:
                    for line in infile:
                        if can_add_targets:
                            target_domains.append(line.strip())
                        if len(target_domains) > self._domain_batch_size - 1:
                            break
                        if last_domain == line.strip():
                            can_add_targets = True
                infile.close()

                with open(self._targets_domains_part_file, "w") as txt_file:
                    for line in target_domains:
                        txt_file.write(f"{line}\n")
                txt_file.close()

            else:
                print(f'DL stopped. {self._targets_domains_file} is missing')
                break

    def __check_batch_domains(self, domain):
        cookie_manager = CookieHelper(domain)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)

        self._request_handler = RequestHandler(cookies=cookies, headers=self._headers)
        print(f'Checking {domain} domain...')
        resp = self._request_handler.send_head_request(f'http://{domain}')
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

        waymore = Waymore(domain, self._request_handler)
        waymore_subdomains = waymore.get_domains()

        massdns_subdomains = set()
        if self._check_mode != 'DL' and self._severity == 1:
            massdns = MassDns(domain)
            massdns_subdomains = massdns.get_subdomains()

        all_subdomains = amass_subdomains \
            .union(knock_subdomains) \
            .union(subfinder_subdomains) \
            .union(massdns_subdomains) \
            .union(waymore_subdomains)

        # dnsx = Dnsx(domain)
        # dnsx.get_dnsx_report(all_subdomains)

        if domain not in all_subdomains:
            all_subdomains.add(domain)

        mysql_repo = MysqlRepository()
        db_subdomains = mysql_repo.get_tracked_subdomains(domain)
        filtered_domains = set([sub for sub in all_subdomains if all(db_sub != sub for db_sub in db_subdomains)])

        subdomain_checker = SubdomainChecker(domain, self._request_handler)
        start_urls_dtos = subdomain_checker.check_all_subdomains(filtered_domains)

        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        db_subdomains.update(filtered_domains)
        if len(start_urls_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live domains found')
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) Found {len(start_urls_dtos)} start urls')

            nmap = Nmap(domain, self._request_handler)
            nmap_get_dtos = nmap.check_ports(start_urls_dtos)
            start_urls_dtos += nmap_get_dtos

            if len(start_urls_dtos) == 0:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live urls found')
            else:
                eyewitness = EyeWitness(domain, self._request_handler)
                eyewitness.visit_dtos(start_urls_dtos)

                nuclei = Nuclei(domain, self._headers)
                nuclei.check_multiple_uls(start_urls_dtos)

                single_url_man = SingleUrlManager(self._headers)
                thread_man = ThreadManager()
                thread_man.run_all(single_url_man.do_run, start_urls_dtos)

                # db_urls.update(set([dto.url for dto in filtered_urls]))
                # mysql_repo.save_tracker_urls_result(domain, db_urls)

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ({domain})')

        mysql_repo.save_tracker_domains_result(domain, db_subdomains)

    def __process_targets(self):
        if os.path.exists(self._targets_domains_part_file):
            domains = list(line.strip() for line in open(self._targets_domains_part_file))
            if len(domains) == 0:
                print(f'No fast urls found - {self._targets_domains_part_file}')
                return

            thread_man = ThreadBucket()
            thread_man.run_all(self.__check_batch_domains, domains, debug_msg=self._tool_name)

            last_domain = domains[len(domains) - 1]
            print(f'Last URL was processed - {last_domain}')
            return last_domain

        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._targets_domains_part_file} is missing')
            return
