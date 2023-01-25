from copy import deepcopy
from datetime import datetime
import urllib.parse as urlparse
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class SstiManager:
    def __init__(self, domain, cookies, headers):
        self._domain = domain
        self._payloads = ['{{88*88}}', '{88*88}', '@(88*88)']
        self._double_check = '77*77'
        self._expected = '7744'
        self._double_check_expected = '5929'
        self._request_handler = RequestHandler(cookies, headers)

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('SstiManager/Get', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[InjectionFoundDTO] = []
            for dto in dtos:
                self.__check_url(dto, result)
                self.__check_get_params(dto, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SstiManager GET found {len(result)} items')

    def __check_url(self, dto: GetRequestDTO, result: List[InjectionFoundDTO]):

        parsed = urlparse.urlparse(dto.url)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}'

        for payload in self._payloads:
            url = f'{base_url}/{payload}'
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(result, response, url, InjectionType.Ssti_Get)

    def __check_get_params(self, dto: GetRequestDTO, result: List[InjectionFoundDTO]):
        url = dto.url
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = url.split(query)
            for payload in self._payloads:
                payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(result, response, url, InjectionType.Ssti_Get)

        return result

    def check_form_requests(self, form_results: List[FormRequestDTO]):
        cache_manager = CacheManager('SstiManager/Form', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[InjectionFoundDTO] = []

            for item in form_results:
                self.__check_form_request(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print("Found FORM SSTI: " + str(len(result)))

    def __check_form_request(self, dto: FormRequestDTO, result: List[InjectionFoundDTO]):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        for payload in self._payloads:
                            payload_params = deepcopy(form.params)
                            payload_params[param] = payload

                            response = self._request_handler.handle_request(dto.url, post_data=payload_params)
                            if response is None:
                                continue

                            self.__check_keywords(result, response, dto.url, InjectionType.Ssti_PostForm, payload_params)

                elif form.method_type == "GET":
                    url = form.action + '?'
                    for param in form.params:
                        for payload in self._payloads:
                            prev_url = url
                            url += f'{param}={payload}&'

                            response = self._request_handler.handle_request(url)
                            if response is None:
                                continue

                            self.__check_keywords(result, response, url, InjectionType.Ssti_Get, param)

                            if response.status_code == 400:
                                url = prev_url
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.url}) - {inst}")

    def __check_keywords(self, result, response, url, inj_type: InjectionType, param=None):
        web_page = response.text
        if self._expected in web_page:
            double_check_url = url.replace('88*88', self._double_check)
            response2 = self._request_handler.handle_request(double_check_url)
            if response2 is None:
                return

            web_page2 = response2.text
            if self._double_check_expected in web_page2:
                substr_index = web_page.find(self._expected)
                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                log_header_msg = f'injFOUND: {self._expected};' \
                                 f'URL: {url}' \
                                 f'DETAILS: {web_page[start_index:last_index]};'
                print(log_header_msg)
                return result.append(InjectionFoundDTO(inj_type, url, param, web_page, log_header_msg))
        if response.status_code == 500:
            print("SstiManager: 500 status - " + url)
