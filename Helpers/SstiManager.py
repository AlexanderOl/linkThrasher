import inject
import urllib.parse as urlparse

from copy import deepcopy
from typing import List
from Common.Logger import Logger
from Common.RequestChecker import RequestChecker
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.FormRequestDTO import FormRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class SstiManager:
    def __init__(self):
        self.errors_500 = []
        self._result = None
        self._payloads = ['{{888*888}}', '{888*888}', '@(888*888)', '${888*888}', '%0a888*888']
        self._double_check = '777*777'
        self._expected = '788544'
        self._double_check_expected = '603729'
        self._logger = inject.instance(Logger)
        self._request_checker = inject.instance(RequestChecker)
        self._request_handler = inject.instance(RequestHandler)
        self._thread_manager = inject.instance(ThreadManager)

    def check_get_requests(self, domain: str, dtos: List[HeadRequestDTO]):

        cache_manager = CacheHelper('SstiManager/Get', domain, 'Results')
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            self._thread_manager.run_all(self.__check_url, dtos, debug_msg=f'SstiManager/Get/Route ({domain})')

            dtos_with_params = {}
            for dto in dtos:
                if ";".join(dto.query_params) not in dtos_with_params and len(dto.query_params) > 0:
                    dtos_with_params[";".join(dto.query_params)] = dto

            self._thread_manager.run_all(self.__check_get_params, list(dtos_with_params.values()),
                                         debug_msg=f'SstiManager/Get/Param ({domain})')

            cache_manager.save_dtos(self._result)

        self._logger.log_warn(f'({domain}) SstiManager GET found {len(self._result)} items')

    def __check_url(self, dto: HeadRequestDTO):

        route_url_payloads = self._request_checker.get_route_payloads(dto.url, self._payloads, check_specific_type=True)

        for url in route_url_payloads:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(response, url, InjectionType.Ssti_Get)

    def __check_get_params(self, dto: HeadRequestDTO):

        payloads_urls = self._request_checker.get_param_payloads(dto.url, self._payloads, 'SSTI')

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(response, url, InjectionType.Ssti_Get)

    def check_form_requests(self, domain: str, form_dtos: List[FormRequestDTO]):
        cache_manager = CacheHelper('SstiManager/Form', domain, 'Results')
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            self._thread_manager.run_all(self.__check_form_request, form_dtos, debug_msg=f'SstiManager/Form ({domain})')

            cache_manager.save_dtos(self._result)

        self._logger.log_warn(f'({domain}) SstiManager FORM SSTI: {len(self._result)}')

    def __check_form_request(self, dto: FormRequestDTO):
        try:
            for form in dto.form_params:

                if any('csrf' in param.lower() for param in form.params):
                    continue

                if form.method_type == "POST":
                    for param in form.params:

                        if self._request_checker.is_form_param_checked(form.method_type, dto.url, param):
                            continue

                        for payload in self._payloads:
                            payload_params = deepcopy(form.params)
                            payload_params[param] = payload

                            response = self._request_handler.handle_request(dto.url, post_data=payload_params)
                            if response is None:
                                continue

                            self.__check_keywords(response, dto.url, InjectionType.Ssti_PostForm, payload_params)

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

                        for payload in self._payloads:
                            prev_url = url
                            url += f'{param}={payload}&'

                            response = self._request_handler.handle_request(url)
                            if response is None:
                                continue

                            self.__check_keywords(response, url, InjectionType.Ssti_Get, param)

                            if response.status_code == 400:
                                url = prev_url
                else:
                    self._logger.log_warn("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            self._logger.log_error(f"Exception - ({dto.url}) - {inst}")

    def __check_keywords(self, response, url, inj_type: InjectionType, param=None):
        web_page = response.text
        if self._expected in web_page:
            double_check_url = url.replace('888*888', self._double_check)
            response2 = self._request_handler.handle_request(double_check_url)
            if response2 is None:
                return

            web_page2 = response2.text
            if self._double_check_expected in web_page2:
                substr_index = web_page.find(self._expected)
                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                details = web_page[start_index:last_index].replace('/n', '').replace('/r', '').strip()
                log_header_msg = f'injFOUND: {self._expected};' \
                                 f'URL: {url}' \
                                 f'DETAILS: {details};'
                self._logger.log_warn(log_header_msg)
                return self._result.append(InjectionFoundDTO(inj_type, url, param, web_page, log_header_msg))
        if response.status_code == 500:
            details = response.text[0:200].replace('\n', '').replace('\r', '').strip()
            self._logger.log_warn(f"SstiManager: 500 status - {url}; DETAILS: {details}")
            self.errors_500.append({'url': url, 'response_len': len(response.text)})
