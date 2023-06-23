import csv
import os

from Managers.DomainFlowManager import DomainFlowManager
from Managers.MultipleUrlFlowManager import MultipleUrlFlowManager


class CsvManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'

    def run(self):
        with open('Targets/scopes.csv', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='|')
            domains = set()
            urls = set()
            for splitted in reader:
                if len(splitted) <= 0:
                    continue

                if len(splitted) >= 5:
                    if splitted[3] == 'true' and splitted[4] == 'true':
                        if splitted[0].startswith('http'):
                            urls.add(splitted[0])
                        elif '*.' in splitted[0]:
                            domains.add(splitted[0].replace('*.', ''))
                        else:
                            domains.add(splitted[0])
                    else:
                        print(f"NotEligible/OOS: {', '.join(splitted)}")

            if len(domains) > 0:
                domain_man = DomainFlowManager(self._headers)
                for domain in domains:
                    domain_man.check_domain(domain)

            if len(urls) > 0:
                multiple_man = MultipleUrlFlowManager(self._headers)
                multiple_man.run(urls)
