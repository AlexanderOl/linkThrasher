import validators
from urllib3 import exceptions, disable_warnings
from datetime import datetime
from Helpers.CacheManager import CacheManager
from Helpers.SubdomainChecker import SubdomainChecker
from Tools.Amass import Amass
from Tools.Knock import Knock
from Tools.MassDns import MassDns
from Tools.SubFinder import SubFinder


class DomainTackerManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        disable_warnings(exceptions.InsecureRequestWarning)

    def track_domains(self, domain: str):

        if not validators.domain(domain):
            print(f'{domain} is not a domain')
            return

        amass = Amass(domain)
        amass_subdomains = amass.get_subdomains()

        knock = Knock(domain)
        knock_subdomains = knock.get_subdomains()

        subfinder = SubFinder(domain)
        subfinder_subdomains = subfinder.get_subdomains()

        massdns = MassDns(domain)
        massdns_subdomains = massdns.get_subdomains()

        all_subdomains = amass_subdomains \
            .union(knock_subdomains) \
            .union(subfinder_subdomains) \
            .union(massdns_subdomains)

        subdomain_checker = SubdomainChecker(domain, self._headers)
        start_urls_dtos = subdomain_checker.check_all_subdomains(all_subdomains)

        cache_man = CacheManager(self._tool_name, domain)
        old_start_urls_dtos = cache_man.get_tracked_subdomains()
        filtered_urls = [dto for dto in start_urls_dtos
                         if all(old_dto.url != dto.url for old_dto in old_start_urls_dtos)]

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: '
              f'DomainTackerManager done with {domain} and found new urls {len(filtered_urls)}')

        if len(filtered_urls) > 0:
            res = old_start_urls_dtos + filtered_urls
            cache_man.save_tracker_result(res)
            print_urls = [dto.url for dto in filtered_urls]
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: Urls {", ".join(print_urls)}')
