from datetime import datetime

import requests
import urllib.parse as urlparse

from typing import List

from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.SstiFoundDTO import SstiFoundDTO, SstiType


class SstiManager:
    def __init__(self, domain,  cookies, headers):
        self.domain = domain
        self.cookies = cookies
        self.headers = headers
        self.payloads = ['{{7*8}}poc', '{7*8}poc', '@(7*8)poc']
        self.expected = '56poc'

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SstiManager GET started...')

        cache_manager = CacheManager('SstiManagerResult/Get', self.domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[SstiFoundDTO] = []
            for dto in dtos:
                self.check_url(dto, result)
                self.check_get_params(dto, result)

            cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SqliManager GET found {len(result)} items')

    def check_url(self, dto: GetRequestDTO, result: List[SstiFoundDTO]):

        parsed = urlparse.urlparse(dto.link)
        base_url = f'{parsed.scheme}://{parsed.hostname}{parsed.path}'

        for payload in self.payloads:
            self.send_ssti_request(f'{base_url}/{payload}', result)

    def check_get_params(self, dto: GetRequestDTO, result: List[SstiFoundDTO]):
        url = dto.link
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = url.split(query)
            for payload in self.payloads:
                payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={payload}{main_url_split[1]}')

        for payload in payloads_urls:
            self.send_ssti_request(payload, result)

        return result

    def check_form_requests(self, form_results: List[FormRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SstiManager FORM started...')

        cache_manager = CacheManager('SstiManagerResult/Form', self.domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[SstiFoundDTO] = []

            for item in form_results:
                self.check_form_request(item, result)

            cache_manager.save_result(result)

        print("Found FORM XSS: " + str(len(result)))

    def send_ssti_request(self, url, result: List[SstiFoundDTO]):
        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            if response.status_code == 200 or str(response.status_code)[0] == '5':
                web_page = response.text
                if self.expected in web_page:
                    print("SstiFinder GET XSS: - " + url)
                    return result.append(SstiFoundDTO(SstiType.Get, url))
            if str(response.status_code)[0] == '5':
                print("SstiFinder: 500 status - " + url)
        except Exception as inst:
            print(inst)
            print("ERROR - " + url)

    def check_form_request(self, dto: FormRequestDTO,  result: List[SstiFoundDTO]):

        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    form_params = form.params
                    for payload in self.payloads:
                        old_param = form_params[param]
                        form_params[param] = payload
                        response = requests.post(dto.link, data=form_params, headers=self.headers, cookies=self.cookies)
                        if response.status_code == 200 or str(response.status_code)[0] == '5':
                            web_page = response.text
                            if self.expected in web_page:
                                print(f'Found FORM XSS! url:{dto.link} , param:{param}, action:{form.action}')
                                result.append(SstiFoundDTO(SstiType.PostForm, dto.link, form_params, web_page))
                        elif response.status_code == 400:
                            form_params[param] = old_param
            elif form.method_type == "GET":
                url = form.action + '?'
                for param in form.params:
                    for payload in self.payloads:
                        url += f'{param}={payload}&'
                        response = requests.get(url, headers=self.headers, cookies=self.cookies)
                        if response.status_code == 200 or str(response.status_code)[0] == '5':
                            web_page = response.text
                            if self.expected in web_page:
                                print(f'Found FORM XSS! url:{url}')
                                result.append(SstiFoundDTO(SstiType.GetForm, dto.link, param, web_page))
                        elif response.status_code == 400:
                            url -= f'{param}={payload}&'
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return
