from copy import deepcopy
import urllib.parse as urlparse
from datetime import datetime
from typing import List
from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class XssManager:
    def __init__(self, domain, cookies, headers):
        self._domain = domain
        self._expected = '<poc>'
        self._injections_to_check = ['syntax', 'xpath', '<poc>', 'internalerror', 'warning: ', 'exception: ']
        self._false_positives = ['malformed request syntax']
        self._request_handler = RequestHandler(cookies, headers)

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('XssManager/Get', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[InjectionFoundDTO] = []
            for dto in dtos:
                url = f'{dto.url}/{self._expected}'
                response = self._request_handler.handle_request(url)
                if response is None:
                    return
                self.__check_keywords(result, response, url, InjectionType.Xss_Get, self._expected,
                                      original_url=dto.url)
                self.__check_params(dto.url, result)
            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found GET XSS: {len(result)}')

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        cache_manager = CacheManager('XssManager/Form', self._domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[InjectionFoundDTO] = []

            for item in form_results:
                self.__check_form(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found FORM XSS: {len(result)}')

    def __check_params(self, original_url, result: List[InjectionFoundDTO]):
        payloads_urls = set()
        parsed = urlparse.urlparse(original_url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = original_url.split(query)
            payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={self._expected}{main_url_split[1]}')

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(result, response, url, InjectionType.Xss_Get, self._expected,
                                  original_url=original_url)

        return result

    def __check_form(self, dto: FormRequestDTO, result: List[InjectionFoundDTO]):
        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    payload = deepcopy(form.params)
                    prev_param = payload[param]
                    payload[param] = self._expected

                    response = self._request_handler.handle_request(dto.url, post_data=payload)
                    if response is None:
                        continue

                    need_to_discard_payload = self.__check_keywords(result, response, dto.url,
                                                                    InjectionType.Xss_PostForm,
                                                                    post_payload=payload,
                                                                    original_post_params=form.params)

                    if need_to_discard_payload:
                        payload[param] = prev_param

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

                    response = self._request_handler.handle_request(url)
                    if response is None:
                        continue

                    need_to_discard_payload = self.__check_keywords(result, response, url, InjectionType.Xss_Get,
                                                                    original_url=dto.url)

                    if response.status_code == 400 or need_to_discard_payload:
                        url = prev_url
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return

    def __check_keywords(self, result,
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
                else:
                    check_response = self._request_handler.handle_request(original_url, post_data=original_post_params)

                if check_response is None or keyword in check_response.text.lower():
                    return

                substr_index = web_page.find(keyword)
                start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                last_index = substr_index + 50 if substr_index + 50 < len(web_page) else substr_index
                log_header_msg = f'injFOUND: {keyword};' \
                                 f'URL: {url};' \
                                 f'DETAILS: {web_page[start_index:last_index]};'
                curr_resp_length = len(web_page)
                if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                           for dto in result):
                    print(log_header_msg)
                    result.append(InjectionFoundDTO(inj_type, url, post_payload, web_page, log_header_msg))
                else:
                    print("Duplicate XSS: - " + url)
                need_to_discard_payload = True

        return need_to_discard_payload
