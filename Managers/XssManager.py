import requests
import urllib.parse as urlparse
from datetime import datetime
from typing import List
from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO
from Models.XssFoundDTO import XssFoundDTO, XssType


class XssManager:
    def __init__(self, domain,  cookies, headers):
        self.domain = domain
        self.cookies = cookies
        self.headers = headers
        self.payload = '<poc>'

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        cache_manager = CacheManager('XssManager/Get', self.domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[XssFoundDTO] = []
            for dto in dtos:
                self.send_xss_request(f'{dto.link}/{self.payload}', result)
                self.check_params(dto.link, result)
            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.domain}) Found GET XSS: {len(result)}')

    def check_form_requests(self, form_results: List[FormRequestDTO]):

        cache_manager = CacheManager('XssManager/Form', self.domain)
        result = cache_manager.get_saved_result()

        if result is None:
            result: List[XssFoundDTO] = []

            for item in form_results:
                self.check_form_request(item, result)

            cache_manager.save_result(result, has_final_result=True)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.domain}) Found FORM XSS: {len(result)}')

    def check_params(self, url, result: List[XssFoundDTO]):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = url.split(query)
            payloads_urls.add(f'{main_url_split[0]}{param_split[0]}={self.payload}{main_url_split[1]}')

        for payload in payloads_urls:
            self.send_xss_request(payload, result)

        return result

    def send_xss_request(self, url, result: List[XssFoundDTO]):
        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            if response.status_code == 200 or str(response.status_code)[0] == '5':
                web_page = response.text
                if self.payload in web_page:
                    print("XssFinder GET XSS: - " + url)
                    return result.append(XssFoundDTO(XssType.Get, url, self.payload, web_page))
            if str(response.status_code)[0] == '5':
                print("XssFinder: 500 status - " + url)
        except Exception as inst:
            print(f"Exception - ({url}) - {inst}")

    def check_form_request(self, dto: FormRequestDTO, result: List[XssFoundDTO]):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        payload = form.params
                        old_param = payload[param]
                        payload[param] = self.payload
                        response = requests.post(dto.link, data=payload, headers=self.headers, cookies=self.cookies)
                        if response.status_code == 200 or str(response.status_code)[0] == '5':
                            web_page = response.text
                            if self.payload in web_page:
                                print(f'Found FORM XSS! url:{dto.link} , param:{param}, action:{form.action}')
                                result.append(XssFoundDTO(XssType.PostForm, dto.link, payload, web_page))
                        elif response.status_code == 400:
                            payload[param] = old_param
                elif form.method_type == "GET":
                    parsed = urlparse.urlparse(dto.link)
                    url_ending = len(form.action) * -1
                    if len(parsed[2]) >= len(form.action) and str(parsed[2])[url_ending:] == form.action:
                        url = f'{parsed[0]}://{parsed[1]}{parsed[2]}?'
                    else:
                        url = form.action + '?'
                    for param in form.params:
                        url += f'{param}={self.payload}&'
                        response = requests.get(url, headers=self.headers, cookies=self.cookies)
                        if response.status_code == 200 or str(response.status_code)[0] == '5':
                            web_page = response.text
                            if self.payload in web_page:
                                print(f'Found FORM XSS! url:{url}')
                                result.append(XssFoundDTO(XssType.GetForm, dto.link, param, web_page))
                        elif response.status_code == 400:
                            url -= f'{param}={self.payload}'
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.link}) - {inst}")

