import requests
import urllib.parse as urlparse
from datetime import datetime
from typing import List
from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.XssFoundDTO import XssFoundDTO, XssType


class XssManager:
    def __init__(self, domain,  cookies, headers):
        self._domain = domain
        self._expected = '<poc>'
        self._request_handler = RequestHandler(cookies, headers)


    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('XssManager/Get', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[XssFoundDTO] = []
            for dto in dtos:
                self.__send_xss_request(f'{dto.url}/{self._expected}', result)
                self.__check_params(dto.url, result)
            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found GET XSS: {len(result)}')

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        cache_manager = CacheManager('XssManager/Form', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[XssFoundDTO] = []

            for item in form_results:
                self.__check_form(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found FORM XSS: {len(result)}')

    def __check_params(self, url, result: List[XssFoundDTO]):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = url.split(query)
            payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={self._expected}{main_url_split[1]}')

        for payload in payloads_urls:
            self.__send_xss_request(payload, result)

        return result

    def __send_xss_request(self, url, result: List[XssFoundDTO]):
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
            curr_resp_length = len(web_page)
            if len(result) == 0 or \
                    len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                print(log_header_msg)
                result.append(XssFoundDTO(XssType.Get, url, self._expected, web_page))
            else:
                print("Duplicate GET XSS: - " + url)
        if str(response.status_code)[0] == '5':
            print("XssManager: 500 status - " + url)

    def __check_form(self, dto: FormRequestDTO, result: List[XssFoundDTO]):
        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    payload = form.params
                    old_param = payload[param]
                    payload[param] = self._expected

                    response = self._request_handler.handle_request(dto.url, post_data=payload)
                    if response is None:
                        continue

                    web_page = response.text
                    if self._expected in web_page:
                        curr_resp_length = len(web_page)
                        if len(result) == 0 or \
                                len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                            print(f'Found FORM XSS! url:{dto.url} , param:{param}, action:{form.action}')
                            result.append(XssFoundDTO(XssType.PostForm, dto.url, payload, web_page))
                        else:
                            print("Duplicate FORM XSS: - " + url)

                    if str(response.status_code)[0] == '5':
                        print("XssManager: 500 status - " + url)
                    elif response.status_code == 400:
                        payload[param] = old_param
            elif form.method_type == "GET":
                parsed = urlparse.urlparse(dto.url)
                url_ending = len(form.action) * -1
                if len(parsed[2]) >= len(form.action) and str(parsed[2])[url_ending:] == form.action:
                    url = f'{parsed[0]}://{parsed[1]}{parsed[2]}?'
                else:
                    url = form.action + '?'
                for param in form.params:
                    prev_url = url
                    url += f'{param}={self._expected}&'

                    response = self._request_handler.handle_request(dto.url)
                    if response is None:
                        continue

                    web_page = response.text
                    if self._expected in web_page:
                        curr_resp_length = len(web_page)
                        if len(result) == 0 or \
                                len(list(filter(lambda dto: dto.response_length == curr_resp_length, result))) < 5:
                            print(f'Found FORM XSS! url:{url}')
                            result.append(XssFoundDTO(XssType.GetForm, dto.url, param, web_page))
                        else:
                            print("Duplicate FORM XSS: - " + url)
                    if response.status_code == 400:
                        url = prev_url
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return

