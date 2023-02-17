import os
from typing import List, Tuple
from urllib.parse import urlparse

import urllib3
from bs4 import BeautifulSoup

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Managers.ThreadManager import ThreadManager
from Managers.XssManager import XssManager
from Models.FormRequestDTO import FormDetailsDTO, FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO


class FastUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._request_handler = RequestHandler(cookies='', headers=headers)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def run(self):
        file_path = 'Targets/fast_urls.txt'
        if os.path.exists(file_path):

            raw_urls = list(line.strip() for line in open(file_path))
            if len(raw_urls) == 0:
                print(f'No fast urls found - {file_path}')
                return
            parsed_parts = urlparse(raw_urls[len(raw_urls)-1])
            cache_key = parsed_parts.netloc
            get_dtos, form_dtos = self.__get_cached_dtos(raw_urls, cache_key)

            xss_manager = XssManager(domain=cache_key, headers=self._headers)
            xss_manager.check_get_requests(get_dtos)
            xss_manager.check_form_requests(form_dtos)

            ssrf_manager = SsrfManager(domain=cache_key, headers=self._headers)
            ssrf_manager.check_get_requests(get_dtos)
            ssrf_manager.check_form_requests(form_dtos)

            sqli_manager = SqliManager(domain=cache_key, headers=self._headers)
            sqli_manager.check_get_requests(get_dtos)
            sqli_manager.check_form_requests(form_dtos)

            ssti_manager = SstiManager(domain=cache_key, headers=self._headers)
            ssti_manager.check_get_requests(get_dtos)
            ssti_manager.check_form_requests(form_dtos)

        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')

    def __get_cached_dtos(self, raw_urls: List[str], cache_key) -> Tuple[List[GetRequestDTO], List[FormRequestDTO]]:

        cache_manager = CacheManager(self._tool_name, cache_key)
        dtos = cache_manager.get_saved_result()
        out_of_scope = self._out_of_scope_urls.split(';')
        self._get_dtos: List[GetRequestDTO] = []
        self._form_dtos: List[FormRequestDTO] = []

        if not dtos and not isinstance(dtos, List):

            filtered_urls = [url for url in raw_urls if all(oos not in url for oos in out_of_scope)]

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url, filtered_urls)

            cache_manager.save_result(
                {'get_dtos': self._get_dtos, 'form_dtos': self._form_dtos},
                cleanup_prev_results=True)
        else:
            out_of_scope = self._out_of_scope_urls.split(';')
            self._get_dtos = list([dto for dto in dtos['get_dtos'] if all(oos not in dto.url for oos in out_of_scope)])
            self._form_dtos = list([dto for dto in dtos['form_dtos'] if all(oos not in dto.url for oos in out_of_scope)])
        return self._get_dtos, self._form_dtos

    def __check_url(self, url):
        response = self._request_handler.handle_request(url)
        if response is None:
            return
        get_dto = GetRequestDTO(url, response)
        self._get_dtos.append(get_dto)
        form_dto = self.__find_forms(url, response.text, get_dto)
        if form_dto:
            self._form_dtos.append(form_dto)
    def __find_forms(self, target_url, web_page, dto: GetRequestDTO):
        if '<form' not in web_page:
            return
        forms = BeautifulSoup(web_page, "html.parser").findAll('form')
        if forms:
            form_details: List[FormDetailsDTO] = []
            for form in forms:
                action_tag = BeautifulSoup(str(form), "html.parser").find('form').get('action')
                if not action_tag:
                    action_tag = target_url
                elif action_tag.startswith('http'):
                    action_tag = action_tag
                elif action_tag.startswith('/'):
                    action_tag = target_url + action_tag

                method = BeautifulSoup(str(form), "html.parser").find('form').get('method')
                method = method if method else "post"
                input_tags = BeautifulSoup(str(form), "html.parser").findAll('input')
                params = {}
                for input_tag in input_tags:
                    param_name = BeautifulSoup(str(input_tag), "html.parser").find('input').get('name')
                    if param_name:
                        default_value = BeautifulSoup(str(input_tag), "html.parser").find('input').get('value')
                        if default_value is None:
                            default_value = ''
                        params[param_name] = default_value
                form_details.append(FormDetailsDTO(action_tag, params, method))
            return FormRequestDTO(target_url, form_details, dto.status_code, dto.response_length)