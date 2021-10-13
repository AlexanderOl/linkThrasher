import os
import uuid
from datetime import datetime
from time import sleep

import requests
import urllib.parse as urlparse

from typing import List
from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.SsrfFoundDTO import SsrfFoundDTO


class SsrfManager:
    def __init__(self, domain, cookies, headers, ngrok_url):
        self.domain = domain
        self.cookies = cookies
        self.headers = headers
        self.ngrok_url = ngrok_url

    def check_get_requests(self, dtos: List[GetRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SsrfManager GET started...')

        if os.path.exists(f'SsrfManagerResult/GET_{self.domain}_log.json'):
            os.remove(f'SsrfManagerResult/GET_{self.domain}_log.json')

        for dto in dtos:
            self.check_params(dto.link)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SsrfManager GET finished')

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SsrfManager FORM started...')

        if os.path.exists(f'SsrfManagerResult/FROM_{self.domain}_log.json'):
            os.remove(f'SsrfManagerResult/FROM_{self.domain}_log.json')

        for item in form_results:
            self.send_ssrf_form_request(item)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SsrfManager FORM finished')

    def check_params(self, url):
        payloads_urls = []
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            csrf_payload = self.get_url_ngrok_payload(url, query)
            payloads_urls.append(csrf_payload)

        for payload in payloads_urls:
            self.send_ssrf_get_request(payload)

    def get_url_ngrok_payload(self, url: str, query: str):
        param_split = query.split('=')
        main_url_split = url.split(query)
        uiid_str = str(uuid.uuid4())
        payload = main_url_split[0] + param_split[0] + f'={self.ngrok_url}{uiid_str}' + main_url_split[1]
        with open(f'Results/SsrfManagerResult/GET_{self.domain}_log.json', 'a') as f:
            f.write(f'{uiid_str}:{payload}\n')
        return payload

    def get_param_ngrok_payload(self, url: str, param: str, method_type: str):
        uiid_str = str(uuid.uuid4())
        payload = f'{self.ngrok_url}{uiid_str}'
        with open(f'Results/SsrfManagerResult/FROM_{self.domain}_log.json', 'a') as f:
            f.write(f'{uiid_str}:{url}:{param}:{method_type}\n')
        return payload

    def send_ssrf_form_request(self, dto: FormRequestDTO):

        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    payload = form.params
                    old_param = payload[param]
                    payload[param] = self.get_param_ngrok_payload(dto.link, param, "POST")
                    response = requests.post(dto.link, data=payload, headers=self.headers, cookies=self.cookies)
                    if response.status_code == 400:
                        payload[param] = old_param
            elif form.method_type == "GET":
                url = form.action + '?'
                for param in form.params:
                    payload = self.get_param_ngrok_payload(dto.link, param, "POST")
                    url += (param + f'={payload}&')
                    response = requests.get(url, headers=self.headers, cookies=self.cookies)
                    if response.status_code == 400:
                        url -= (param + f'={payload}&')
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return

    def send_ssrf_get_request(self, payload):
        try:
            requests.get(payload, headers=self.headers, cookies=self.cookies)
        except Exception as inst:
            print(inst)
            sleep(5)

