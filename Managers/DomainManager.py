import os
import inject
import validators

from datetime import datetime
from Common.Logger import Logger
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
    def __init__(self):
        self._download_path = os.environ.get('download_path')
        self._check_mode = os.environ.get('check_mode')
        self._out_of_scope = os.environ.get("out_of_scope")
        self._domain_batch_size = int(os.environ.get("domain_batch_size"))
        self._severity = int(os.environ.get("severity"))
        self._targets_domains_file = 'Targets/domains.txt'
        self._targets_domains_part_file = 'Targets/domains_part.txt'
        self._tool_name = self.__class__.__name__

        self._request_handler = inject.instance(RequestHandler)
        self._single_url_man = inject.instance(SingleUrlManager)
        self._thread_man = inject.instance(ThreadManager)
        self._nuclei = inject.instance(Nuclei)
        self._amass = inject.instance(Amass)
        self._knock = inject.instance(Knock)
        self._waymore = inject.instance(Waymore)
        self._logger = inject.instance(Logger)
        self._nmap = inject.instance(Nmap)
        self._eyewitness = inject.instance(EyeWitness)
        self._thread_bucket = inject.instance(ThreadBucket)
        self._subdomain_checker = inject.instance(SubdomainChecker)
        self._mysql_repository = inject.instance(MysqlRepository)
        self._cookie_manager = inject.instance(CookieHelper)

    def check_ip(self, ip):
        ips = set()
        ips.add(ip)

        start_urls_dtos = self._subdomain_checker.check_all_subdomains(ip, ips)

        out_of_scope = [x for x in self._out_of_scope.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        if len(start_urls_dtos) == 0:
            self._logger.log_info(f'({ip}) No live urls found at ip')
            return
        else:
            self._logger.log_info(f'({ip}) Found {len(start_urls_dtos)} start urls at ip')

        nmap_head_dtos = self._nmap.check_ports(ip, start_urls_dtos)
        start_urls_dtos += nmap_head_dtos

        self._eyewitness.visit_dtos(ip, start_urls_dtos)

        self._nuclei.check_multiple_uls(ip, start_urls_dtos)

        self._thread_man.run_all(self._single_url_man.do_run, start_urls_dtos, f' ({ip})')

        self._logger.log_info(f'DomainFlowManager done with ip ({ip})')

    def check_multiple_domains(self):

        if self._domain_batch_size == 0:
            with open(self._targets_domains_file) as infile:
                domains = [line.strip() for line in infile]
                for domain in domains:
                    self.__check_batch_domains(domain.strip())
            infile.close()
            return
        while True:
            last_domain = self.__process_targets()
            if not last_domain:
                self._logger.log_info('DomainList finished...')
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
                self._logger.log_warn(f'DL stopped. {self._targets_domains_file} is missing')
                break

    def __check_batch_domains(self, domain):

        cookies = self._cookie_manager.get_cookies_dict(domain)
        self._logger.log_info(f'Checking {domain} domain...')
        resp = self._request_handler.send_head_request(f'http://{domain}', cookies)
        if resp is None:
            return
        self._logger.log_info(f'Domain {domain} init status - {resp.status_code}')
        self.check_domain(domain)
        self._logger.log_info(f'Check {domain} finished!')

    def check_domain(self, domain):
        domain = domain.lower().replace('www.', '')
        if not validators.domain(domain):
            self._logger.log_info(f'{domain} is not a domain')
            return

        amass_subdomains = self._amass.get_subdomains(domain)

        knock_subdomains = self._knock.get_subdomains(domain)

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains()

        waymore_subdomains = self._waymore.get_domains(domain)

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

        db_subdomains = self._mysql_repository.get_tracked_subdomains(domain)
        filtered_domains = set([sub for sub in all_subdomains if all(db_sub != sub for db_sub in db_subdomains)])

        start_urls_dtos = self._subdomain_checker.check_all_subdomains(domain, filtered_domains)

        out_of_scope = [x for x in self._out_of_scope.split(';') if x]
        start_urls_dtos = [dto for dto in start_urls_dtos if all(oos not in dto.url for oos in out_of_scope)]

        db_subdomains.update(filtered_domains)
        if len(start_urls_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live domains found')
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) Found {len(start_urls_dtos)} start urls')

            nmap_get_dtos = self._nmap.check_ports(domain, start_urls_dtos)
            start_urls_dtos += nmap_get_dtos

            if len(start_urls_dtos) == 0:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) No live urls found')
            else:
                self._eyewitness.visit_dtos(domain, start_urls_dtos)

                self._nuclei.check_multiple_uls(domain, start_urls_dtos)

                self._thread_man.run_all(self._single_url_man.do_run, start_urls_dtos)

                # db_urls.update(set([dto.url for dto in filtered_urls]))
                # self._mysql_repository.save_tracker_urls_result(domain, db_urls)

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: DomainFlowManager done with ({domain})')

        self._mysql_repository.save_tracker_domains_result(domain, db_subdomains)

    def __process_targets(self):
        if os.path.exists(self._targets_domains_part_file):
            domains = list(line.strip() for line in open(self._targets_domains_part_file))
            if len(domains) == 0:
                print(f'No fast urls found - {self._targets_domains_part_file}')
                return

            self._thread_bucket.run_all(self.__check_batch_domains, domains, debug_msg=self._tool_name)

            last_domain = domains[len(domains) - 1]
            print(f'Last URL was processed - {last_domain}')
            return last_domain

        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._targets_domains_part_file} is missing')
            return
