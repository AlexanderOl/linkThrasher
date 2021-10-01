from datetime import datetime

import requests
import urllib.parse as urlparse

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

    def check_get_requests(self, dtos: List[GetRequestDTO]):

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: XssManager GET started...')

        cacheManager = CacheManager('XssManagerGetResult', self.domain)
        result = cacheManager.get_saved_result()

        if result is None:
            result: List[XssFoundDTO] = []
            for dto in dtos:
                self.send_xss_request(dto.link + "/<poc>", result)
                self.check_params(dto.link, result)
            cacheManager.save_result(result)

        print("Found GET XSS: " + str(len(result)))

    def check_form_requests(self, form_results: List[FormRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: XssManager FORM started...')

        cacheManager = CacheManager('XssManagerFormResult', self.domain)
        result = cacheManager.get_saved_result()

        if not result:
            result: List[XssFoundDTO] = []

            for item in form_results:
                self.check_form_request(item, result)

            cacheManager.save_result(result)

        print("Found FORM XSS: " + str(len(result)))

    def check_params(self, url, result: List[XssFoundDTO]):
        payloads_urls = []
        parsed = urlparse.urlparse(url)
        queries = filter(None, parsed.query.split("&"))

        for query in queries:
            param_split = query.split('=')
            main_url_split = url.split(query)
            payloads_urls.append(main_url_split[0] + param_split[0] + '=<poc>' + main_url_split[1])

        for payload in payloads_urls:
            self.send_xss_request(payload, result)

        return result

    def send_xss_request(self, url, result: List[XssFoundDTO]):
        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies)
            if response.status_code == 200 or response.status_code == 500:
                web_page = response.text
                if '<poc>' in web_page:
                    print("XssFinder GET XSS: - " + url)
                    return result.append(XssFoundDTO(XssType.Get, url, '<poc>', web_page))
            if response.status_code == 500:
                print("XssFinder: 500 status - " + url)
        except Exception as inst:
            print(inst)
            print("ERROR - " + url)

    def check_form_request(self, dto: FormRequestDTO,  result: List[XssFoundDTO]):

        for form in dto.form_params:
            if form.method_type == "POST":
                for param in form.params:
                    payload = form.params
                    old_param = payload[param]
                    payload[param] = '<poc>'
                    response = requests.post(dto.link, data=payload, headers=self.headers, cookies=self.cookies)
                    if response.status_code == 200 or response.status_code == 500:
                        web_page = response.text
                        if '<poc>' in web_page:
                            print(f'Found FORM XSS! url:{dto.link} , param:{param}, action:{form.action}')
                            result.append(XssFoundDTO("POST", dto.link, payload, web_page))
                    elif response.status_code == 400:
                        payload[param] = old_param
            elif form.method_type == "GET":
                url = form.action + '?'
                for param in form.params:
                    url += (param + '=<poc>&')
                    response = requests.get(url, headers=self.headers, cookies=self.cookies)
                    if response.status_code == 200 or response.status_code == 500:
                        web_page = response.text
                        if '<poc>' in web_page:
                            print(f'Found FORM XSS! url:{dto.link} , param:{param}, action:{form.action}')
                            result.append(XssFoundDTO("GET", dto.link, param, web_page))
                    elif response.status_code == 400:
                        url -= (param + '=<poc>&')
            else:
                print("METHOD TYPE NOT FOUND: " + form.method_type)
                return
