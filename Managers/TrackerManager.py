import os
import validators

from urllib3 import exceptions, disable_warnings
from datetime import datetime

from Common.ThreadManager import ThreadManager
from Dal.MysqlRepository import MysqlRepository
from Helpers.SubdomainChecker import SubdomainChecker
from Managers.SingleUrlManager import SingleUrlManager
from Tools.Amass import Amass
from Tools.Knock import Knock
from Tools.MassDns import MassDns
from Tools.SubFinder import SubFinder


class TrackerManager:
    def __init__(self, headers):
        self._headers = headers
        self._file_path = 'Targets/track_domains.txt'
        self._tool_name = self.__class__.__name__
        disable_warnings(exceptions.InsecureRequestWarning)

    def track_domains(self):

        if os.path.exists(self._file_path):
            domains = list(set(line.strip() for line in open(self._file_path)))

            counter = len(domains)
            for domain in domains:
                print(f'Checking {domain} domain. Counter: {counter}')
                self.__do_track_domain(domain)
                counter -= 1
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._file_path} is missing')

    def __do_track_domain(self, domain):
        if not validators.domain(domain):
            print(f'{domain} is not a domain')
            return

        avoid_cache = True

        amass = Amass(domain)
        amass_subdomains = amass.get_subdomains(avoid_cache=avoid_cache)

        knock = Knock(domain)
        knock_subdomains = knock.get_subdomains(avoid_cache=avoid_cache)

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains(avoid_cache=avoid_cache)

        massdns = MassDns(domain)
        massdns_subdomains = massdns.get_subdomains(avoid_cache=avoid_cache)

        all_subdomains = amass_subdomains \
            .union(knock_subdomains) \
            .union(subfinder_subdomains) \
            .union(massdns_subdomains)

        subdomain_checker = SubdomainChecker(domain, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(all_subdomains, avoid_cache=False)

        mysql_repo = MysqlRepository()
        prev_urls = mysql_repo.get_tracked_subdomains(domain)

        filtered_urls = set([dto.url for dto in start_urls_dtos if all(url != dto.url for url in prev_urls)])

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: '
              f'TackerManager done with {domain} and found new urls {len(filtered_urls)}')

        if len(filtered_urls) > 0:
            prev_urls.update(filtered_urls)
            mysql_repo.save_tracker_result(domain, prev_urls)
            print_urls = "\n".join([url for url in filtered_urls])
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: Urls {print_urls}')

            single_url_man = SingleUrlManager(self._headers)
            thread_man = ThreadManager()
            thread_man.run_all(single_url_man.do_run, filtered_urls)
