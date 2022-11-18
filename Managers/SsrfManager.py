import os
import uuid
import requests
import urllib.parse as urlparse
from typing import List
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from time import sleep
from datetime import datetime


class SsrfManager:

    def __init__(self, domain, cookies, headers, ngrok_url):
        self.domain = domain
        self.cookies = cookies
        self.headers = headers
        self.ngrok_url = ngrok_url
        self.url_params = ['url', 'redirect']

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        if os.path.exists(f'SsrfManagerResult/GET_{self.domain}_log.json'):
            os.remove(f'SsrfManagerResult/GET_{self.domain}_log.json')

        for dto in dtos:
            self.__check_params(dto.link)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.domain}) SsrfManager GET finished')

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        if os.path.exists(f'SsrfManagerResult/FROM_{self.domain}_log.json'):
            os.remove(f'SsrfManagerResult/FROM_{self.domain}_log.json')

        for item in form_results:
            self.__send_ssrf_form_request(item)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.domain}) SsrfManager FORM finished')

    def __check_params(self, url):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = [s for s in parsed.query.split("&") if any(xs in str(s).lower() for xs in self.url_params)]

        for query in queries:
            csrf_payload = self.__get_url_ngrok_payload(url, query)
            payloads_urls.add(csrf_payload)

        for payload in payloads_urls:
            self.__send_ssrf_get_request(payload)

    def __get_url_ngrok_payload(self, url: str, query: str):
        param_split = query.split('=')
        main_url_split = url.split(query)
        uiid_str = str(uuid.uuid4())
        payload = main_url_split[0] + param_split[0] + f'={self.ngrok_url}{uiid_str}' + main_url_split[1]
        with open(f'Results/SsrfManagerResult/GET_{self.domain}_log.json', 'a') as f:
            f.write(f'{uiid_str}:{payload}\n')
        return payload

    def __get_param_ngrok_payload(self, url: str, param: str, method_type: str):
        uiid_str = str(uuid.uuid4())
        payload = f'{self.ngrok_url}{uiid_str}'
        with open(f'Results/SsrfManagerResult/FROM_{self.domain}_log.json', 'a') as f:
            f.write(f'{uiid_str}:{url}:{param}:{method_type}\n')
        return payload

    def __send_ssrf_form_request(self, dto: FormRequestDTO):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        if any(s in str(param).lower() for s in self.url_params):
                            payload = form.params
                            old_param = payload[param]
                            payload[param] = self.__get_param_ngrok_payload(dto.link, param, "POST")
                            response = requests.post(dto.link, data=payload, headers=self.headers, cookies=self.cookies)
                            if response.status_code == 400:
                                payload[param] = old_param
                elif form.method_type == "GET":
                    url = form.action + '?'
                    for param in form.params:
                        if any(s in str(param).lower() for s in self.url_params):
                            payload = self.__get_param_ngrok_payload(dto.link, param, "POST")
                            url += (param + f'={payload}&')
                            response = requests.get(url, headers=self.headers, cookies=self.cookies)
                            if response.status_code == 400:
                                url -= (param + f'={payload}&')
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.link}) - {inst}")

    def __send_ssrf_get_request(self, payload):
        try:
            requests.get(payload, headers=self.headers, cookies=self.cookies)
        except Exception as inst:
            print(inst)
            sleep(5)
