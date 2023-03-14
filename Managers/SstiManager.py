import urllib
from copy import deepcopy
from datetime import datetime
import urllib.parse as urlparse
from typing import List

from Managers.CacheManager import CacheManager
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.InjectionFoundDTO import InjectionType, InjectionFoundDTO


class SstiManager:
    def __init__(self, domain, cookies='', headers={}):
        self.errors_500 = []
        self._result = None
        self._domain = domain
        self._payloads = ['{{888*888}}', '{888*888}', '@(888*888)']
        self._double_check = '777*777'
        self._expected = '788544'
        self._double_check_expected = '603729'
        self._request_handler = RequestHandler(cookies, headers)

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('SstiManager/Get', self._domain)
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url, dtos)
            thread_man.run_all(self.__check_get_params, dtos)

            cache_manager.save_result(self._result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SstiManager GET found {len(self._result)} items')

    def __check_url(self, dto: GetRequestDTO):

        parsed = urllib.parse.urlparse(dto.url)
        route_parts = [r for r in parsed.path.split('/') if r.strip()]
        route_url_payloads = []

        for index, part in enumerate(route_parts):
            for payload in self._payloads:
                payload_part = f'{part}{payload}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'
                route_url_payloads.append(new_url)

        for url in route_url_payloads:
            response = self._request_handler.handle_request(url)
            if response is None:
                return
            self.__check_keywords(response, url, InjectionType.Ssti_Get)

    def __check_get_params(self, dto: GetRequestDTO):
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
            self.__check_keywords(response, url, InjectionType.Ssti_Get)

    def check_form_requests(self, form_dtos: List[FormRequestDTO]):
        cache_manager = CacheManager('SstiManager/Form', self._domain)
        self._result = cache_manager.get_saved_result()

        if self._result is None:
            self._result: List[InjectionFoundDTO] = []

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_form_request, form_dtos)

            cache_manager.save_result(self._result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) SstiManager FORM SSTI: {len(self._result)}')

    def __check_form_request(self, dto: FormRequestDTO):
        try:
            for form in dto.form_params:

                if any('csrf' in param.lower() for param in form.params):
                    continue

                if form.method_type == "POST":
                    for param in form.params:
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
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.url}) - {inst}")

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
                details = web_page[start_index:last_index].replace('/n','').replace('/r','').strip()
                log_header_msg = f'injFOUND: {self._expected};' \
                                 f'URL: {url}' \
                                 f'DETAILS: {details};'
                print(log_header_msg)
                return self._result.append(InjectionFoundDTO(inj_type, url, param, web_page, log_header_msg))
        if response.status_code == 500:
            details = response.text[0:200].replace('\n', '').replace('\r', '').strip()
            print(f"SstiManager: 500 status - {url}; DETAILS: {details}")
            self.errors_500.append({'url': url, 'response': response})

