import os
import urllib
import uuid
import urllib.parse as urlparse
from copy import deepcopy
from typing import List

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.InjectionFoundDTO import InjectionFoundDTO, InjectionType


class SsrfManager:

    def __init__(self, domain, cookies, headers):
        self._domain = domain
        ngrok_url = os.environ.get('ngrok_url')
        self._ngrok_url_safe = urllib.parse.quote(ngrok_url, safe='')
        self._url_params = ['url', 'redirect', 'file', 'page', 'source']
        self._tool_dir = f'Results/SsrfManager'
        self._get_domain_log = f'{self._tool_dir}/GET_{self._domain}_uids.txt'
        self._form_domain_log = f'{self._tool_dir}/FORM_{self._domain}_uids.txt'
        self._request_handler = RequestHandler(cookies, headers)

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        if not os.path.exists(self._tool_dir):
            os.makedirs(self._tool_dir)

        if not os.path.exists(self._get_domain_log):
            cache_manager = CacheManager('SsrfManager/Get', self._domain)
            results: List[InjectionFoundDTO] = []
            for dto in dtos:
                self.__check_route_params(dto.url, results)
            cache_manager.save_result(results, has_final_result=True)

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        if not os.path.exists(self._form_domain_log):
            cache_manager = CacheManager('SsrfManager/Form', self._domain)
            results: List[InjectionFoundDTO] = []
            for item in form_results:
                self.__send_ssrf_form_request(item, results)
            cache_manager.save_result(results, has_final_result=True)

    def __check_route_params(self, url, results: List[InjectionFoundDTO]):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = [s for s in parsed.query.split("&") if any(xs in str(s).lower() for xs in self._url_params)]

        for query in queries:
            csrf_payload = self.__get_url_ngrok_payload(url, str(query))
            payloads_urls.add(csrf_payload)

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is not None and \
                    str(response.status_code).startswith('3') and \
                    'ngrok' in response.headers['Location']:
                msg = f'OPEN REDIRECT in GET FOUND! url: {url}'
                print(msg)
                results.append(
                    InjectionFoundDTO(InjectionType.Open_Redirect_POST, url, self._ngrok_url_safe, response.text, msg))

    def __get_url_ngrok_payload(self, url: str, query: str):
        param_split = query.split('=')
        main_url_split = url.split(query)
        uid_str = str(uuid.uuid4())
        payload = main_url_split[0] + param_split[0] + f'={self._ngrok_url_safe}{uid_str}' + main_url_split[1]
        with open(self._get_domain_log, 'a') as f:
            f.write(f'{uid_str}:{payload}\n')
        return payload

    def __get_param_ngrok_payload(self, url: str, param: str, method_type: str):
        uid_str = str(uuid.uuid4())
        payload = f'{self._ngrok_url_safe}{uid_str}'
        with open(self._get_domain_log, 'a') as f:
            f.write(f'{uid_str}:{url}:{param}:{method_type}\n')
        return payload

    def __send_ssrf_form_request(self, dto: FormRequestDTO, results: List[InjectionFoundDTO]):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params):
                            payload = deepcopy(form.params)
                            payload[param] = self.__get_param_ngrok_payload(dto.url, param, "POST")

                            response = self._request_handler.handle_request(dto.url, post_data=payload)
                            if response is not None and \
                                    str(response.status_code).startswith('3') and \
                                    'ngrok' in response.headers['Location']:
                                msg = f'OPEN REDIRECT in POST FOUND! param: {param}, url: {dto.url}'
                                print(msg)
                                results.append(InjectionFoundDTO(InjectionType.Open_Redirect_POST, dto.url, param, response.text, msg))

                elif form.method_type == "GET":
                    url = form.action + '?'
                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params):
                            payload = self.__get_param_ngrok_payload(dto.url, param, "POST")
                            prev_url = url
                            url += (param + f'={payload}&')

                            response = self._request_handler.handle_request(url)
                            if response is not None and \
                                    str(response.status_code).startswith('3') and \
                                    'ngrok' in response.headers['Location']:
                                msg = f'OPEN REDIRECT in GET FOUND! param: {param}, url: {dto.url}'
                                print(msg)
                                results.append(
                                    InjectionFoundDTO(InjectionType.Open_Redirect_GET, dto.url, param, response.text, msg))
                            if response.status_code == 400:
                                url = prev_url
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.url}) - {inst}")
