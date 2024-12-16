import urllib.parse as urlparse
from copy import deepcopy
from typing import List

import inject

from Common.Logger import Logger
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.FormRequestDTO import FormRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class XssManager:
    def __init__(self):
        self._result = None
        self._expected = ['<poc>', '""poc\'\'']
        self._injections_to_check = ['<poc>', '""poc\'\'']
        self._logger = inject.instance(Logger)
        self._request_checker = inject.instance(RequestChecker)
        self._request_handler = inject.instance(RequestHandler)
        self._thread_manager = inject.instance(ThreadManager)

    def check_get_requests(self, domain: str, dtos: List[HeadRequestDTO]):

        cache_manager = CacheHelper('XssManager/Get', domain, 'Results')
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            self._thread_manager.run_all(self.__check_route, dtos, debug_msg=f'XssManager/Get/Route ({domain})')
            dtos_with_params = {}
            for dto in dtos:
                if ";".join(dto.query_params) not in dtos_with_params and len(dto.query_params) > 0:
                    dtos_with_params[";".join(dto.query_params)] = dto

            self._thread_manager.run_all(self.__check_params, list(dtos_with_params.values()),
                                         debug_msg=f'XssManager/Get/Param ({domain})')

            cache_manager.save_dtos(self._result)

        self._logger.log_warn(f'({domain}) Found GET XSS: {len(self._result)}')

    def check_form_requests(self, domain: str, form_dtos: List[FormRequestDTO]):

        cache_manager = CacheHelper('XssManager/Form', domain, 'Results')
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            self._thread_manager.run_all(self.__check_form, form_dtos, debug_msg=f'XssManager/Form ({domain})')

            cache_manager.save_dtos(self._result)

        self._logger.log_warn(f'({domain}) Found FORM XSS: {len(self._result)}')

    def __check_params(self, dto: HeadRequestDTO):

        payloads_urls = self._request_checker.get_param_payloads(dto.url, self._injections_to_check, 'XSS')

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is None:
                return

            self.__check_keywords(response, url, InjectionType.Xss_Get, original_url=dto.url)

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
                self._logger.log_error("METHOD TYPE NOT FOUND: " + form.method_type)
                return

        if any(form for form in dto.form_params if form.method_type == "POST"):
            response = self._request_handler.handle_request(dto.parent_url)
            if response is None:
                return

            self.__check_keywords(response, dto.url, InjectionType.Xss_Stored)

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
            if keyword in web_page:

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
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else len(web_page) - 1
                mime_type = ''
                if "Content-Type" in response.headers:
                    mime_type = response.headers["Content-Type"]

                if 'text/html' not in mime_type:
                    self._logger.log_warn(f'URL: ({url}) with wrong mime-type: {mime_type}')
                    return
                details = web_page[start_index:last_index].replace('/n', '').replace('/r', '').strip()
                log_header_msg = f'injFOUND: {keyword};' \
                                 f'MIME-TYPE: {mime_type};' \
                                 f'URL: {url};' \
                                 f'DETAILS: {details};'
                curr_resp_length = len(web_page)
                if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                           for dto in self._result):
                    self._logger.log_warn(log_header_msg)
                    self._result.append(InjectionFoundDTO(inj_type, url, post_payload, web_page, log_header_msg))
                else:
                    self._logger.log_warn("Duplicate XSS: - " + url)
                need_to_discard_payload = True

        return need_to_discard_payload

    def __check_route(self, dto: HeadRequestDTO):

        route_url_payloads = self._request_checker.get_route_payloads(dto.url, self._injections_to_check)
        route_url_payloads.append(f"{dto.url}?{self._injections_to_check[0]}={self._injections_to_check[1]}")

        for url in route_url_payloads:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(response, url, InjectionType.Xss_Get, original_url=dto.url)
