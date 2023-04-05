import urllib
from copy import deepcopy
import urllib.parse as urlparse
from datetime import datetime
from typing import List

from Common.RequestChecker import RequestChecker
from Managers.CacheManager import CacheManager
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class XssManager:
    def __init__(self, domain, cookies='', headers={}):
        self._result = None
        self._domain = domain
        self._expected = ['<poc>', '""poc\'\'']
        self._injections_to_check = ['<poc>', '""poc\'\'']
        # self._injections_to_check = ['syntax', 'xpath', '<poc>', '""poc\'\'', 'internalerror', 'warning: ', 'exception: ']
        self._false_positives = ['malformed request syntax',
                                 'eval|internal|range|reference|syntax|type']
        self._request_handler = RequestHandler(cookies, headers)
        self._request_checker = RequestChecker()

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('XssManager/Get', self._domain)
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_route_params, dtos)

            cache_manager.save_result(self._result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found GET XSS: {len(self._result)}')

    def check_form_requests(self, form_dtos: List[FormRequestDTO]):

        cache_manager = CacheManager('XssManager/Form', self._domain)
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_form, form_dtos)

            cache_manager.save_result(self._result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found FORM XSS: {len(self._result)}')

    def __check_params(self, original_url):
        payloads_urls = set()
        parsed = urlparse.urlparse(original_url)
        param_key_values = filter([], parsed.query.split("&"))

        for param_k_v in param_key_values:

            if self._request_checker.is_get_param_checked(original_url, param_k_v):
                continue

            main_url_split = original_url.split(param_k_v)
            param_key = param_k_v.split('=')[0]
            for exp in self._expected:
                payloads_urls.add(f'{main_url_split[0]}{param_key}={exp}{main_url_split[1]}')

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is None:
                return

            self.__check_keywords(response, url, InjectionType.Xss_Get, original_url=original_url)

    def __check_form(self, dto: FormRequestDTO):
        for form in dto.form_params:
            if any('csrf' in param.lower() for param in form.params):
                continue
            if form.method_type == "POST":
                for param in form.params:

                    if self._request_checker.is_form_param_checked(form.method_type, dto.url, param):
                        continue

                    payload = deepcopy(form.params)
                    prev_param = payload[param]
                    for exp in self._expected:
                        payload[param] = exp

                        response = self._request_handler.handle_request(dto.url, post_data=payload)
                        if response is None:
                            continue

                        need_to_discard_payload = self.__check_keywords(response, dto.url,
                                                                        InjectionType.Xss_PostForm,
                                                                        post_payload=payload,
                                                                        original_post_params=form.params)

                        if need_to_discard_payload:
                            payload[param] = prev_param

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

                    prev_url = url
                    for exp in self._expected:
                        url += f'{param}={exp}&'

                        response = self._request_handler.handle_request(url)
                        if response is None:
                            continue

                        need_to_discard_payload = self.__check_keywords(response, url, InjectionType.Xss_Get,
                                                                        original_url=dto.url)

                        if response.status_code == 400 or need_to_discard_payload:
                            url = prev_url
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return

        if any(form for form in dto.form_params if form.method_type == "POST"):
            response = self._request_handler.handle_request(dto.parent_url)
            if response is None:
                return

            self.__check_keywords(response, dto.parent_url, InjectionType.Xss_Stored)

    def __check_keywords(self,
                         response,
                         url,
                         inj_type: InjectionType,
                         post_payload=None,
                         original_url: str = None,
                         original_post_params=None):
        web_page = response.text
        need_to_discard_payload = False
        for keyword in self._injections_to_check:
            if keyword in web_page and not any(word in web_page for word in self._false_positives):

                if original_url is not None:
                    check_response = self._request_handler.handle_request(original_url)
                    if check_response is None or keyword in check_response.text.lower():
                        return
                elif original_post_params is not None:
                    check_response = self._request_handler.handle_request(url, post_data=original_post_params)
                    if check_response is None or keyword in check_response.text.lower():
                        return

                substr_index = web_page.find(keyword)
                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                mime_type = ''
                if "Content-Type" in response.headers:
                    mime_type = response.headers["Content-Type"]

                if 'text/html' not in mime_type:
                    print(f'Url ({url}) with wrong mime-type: {mime_type}')
                    return
                details = web_page[start_index:last_index].replace('/n', '').replace('/r', '').strip()
                log_header_msg = f'injFOUND: {keyword};' \
                                 f'MIME-TYPE: {mime_type};' \
                                 f'URL: {url};' \
                                 f'DETAILS: {details};'
                curr_resp_length = len(web_page)
                if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                           for dto in self._result):
                    print(log_header_msg)
                    self._result.append(InjectionFoundDTO(inj_type, url, post_payload, web_page, log_header_msg))
                else:
                    print("Duplicate XSS: - " + url)
                need_to_discard_payload = True

        return need_to_discard_payload

    def __check_route_params(self, dto: GetRequestDTO):
        parsed = urllib.parse.urlparse(dto.url)
        route_parts = [r for r in parsed.path.split('/') if r.strip()]
        route_url_payloads = []

        for index, part in enumerate(route_parts):

            if self._request_checker.is_route_checked(dto.url, part):
                continue

            for exp in self._expected:
                payload_part = f'{part}{exp}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'
                route_url_payloads.append(new_url)

        for url in route_url_payloads:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(response, url, InjectionType.Xss_Get, original_url=dto.url)

        self.__check_params(dto.url)
