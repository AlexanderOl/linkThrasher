from datetime import datetime
import urllib.parse as urlparse
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.SstiFoundDTO import SstiFoundDTO, SstiType


class SstiManager:
    def __init__(self, domain, cookies, headers):
        self._domain = domain
        self._payloads = ['{{7*8}}poc', '{7*8}poc', '@(7*8)poc']
        self._expected = '56poc'
        self._request_handler = RequestHandler(cookies, headers)

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('SstiManager/Get', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[SstiFoundDTO] = []
            for dto in dtos:
                self.__check_url(dto, result)
                self.__check_get_params(dto, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SqliManager GET found {len(result)} items')

    def __check_url(self, dto: GetRequestDTO, result: List[SstiFoundDTO]):

        parsed = urlparse.urlparse(dto.url)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}'

        for payload in self._payloads:
            self.__send_ssti_request(f'{base_url}/{payload}', result)

    def __check_get_params(self, dto: GetRequestDTO, result: List[SstiFoundDTO]):
        url = dto.url
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = url.split(query)
            for payload in self._payloads:
                payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for payload in payloads_urls:
            self.__send_ssti_request(payload, result)

        return result

    def check_form_requests(self, form_results: List[FormRequestDTO]):
        cache_manager = CacheManager('SstiManager/Form', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[SstiFoundDTO] = []

            for item in form_results:
                self.__check_form_request(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print("Found FORM XSS: " + str(len(result)))

    def __send_ssti_request(self, url, result: List[SstiFoundDTO]):
        response = self._request_handler.handle_request(url)
        if response is None:
            return
        web_page = response.text
        if self._expected in web_page:
            substr_index = web_page.find(self._expected)
            start_index = substr_index - 50 if substr_index - 50 > 0 else 0
            last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
            log_header_msg = f'injFOUND "{self._expected}":' \
                             f'STATUS-{response.status_code};' \
                             f'DETAILS-{web_page[start_index:last_index]};'
            print(log_header_msg)
            return result.append(SstiFoundDTO(SstiType.Get, url))
        if str(response.status_code)[0] == '5':
            print("SstiManager: 500 status - " + url)

    def __check_form_request(self, dto: FormRequestDTO, result: List[SstiFoundDTO]):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        form_params = form.params
                        for payload in self._payloads:
                            old_param = form_params[param]
                            form_params[param] = payload

                            response = self._request_handler.handle_request(dto.link, post_data=form_params)
                            if response is None:
                                continue

                            web_page = response.text
                            if self._expected in web_page:
                                substr_index = web_page.find(self._expected)
                                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                                log_header_msg = f'injFOUND "{self._expected}":' \
                                                 f'STATUS-{response.status_code};' \
                                                 f'DETAILS-{web_page[start_index:last_index]};'
                                print(log_header_msg)
                                result.append(SstiFoundDTO(SstiType.PostForm, dto.link, form_params, web_page))
                            if str(response.status_code)[0] == '5':
                                print("SstiManager: 500 status - " + url)
                            elif response.status_code == 400:
                                form_params[param] = old_param
                elif form.method_type == "GET":
                    url = form.action + '?'
                    for param in form.params:
                        for payload in self._payloads:
                            prev_url = url
                            url += f'{param}={payload}&'

                            response = self._request_handler.handle_request(url)
                            if response is None:
                                continue

                            if self._expected in web_page:
                                substr_index = web_page.find(self._expected)
                                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                                log_header_msg = f'injFOUND "{self._expected}":' \
                                                 f'STATUS-{response.status_code};' \
                                                 f'DETAILS-{web_page[start_index:last_index]};'
                                print(log_header_msg)
                                result.append(SstiFoundDTO(SstiType.GetForm, dto.link, param, web_page))
                            if str(response.status_code)[0] == '5':
                                print("SstiManager: 500 status - " + url)
                            elif response.status_code == 400:
                                url = prev_url
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.link}) - {inst}")
