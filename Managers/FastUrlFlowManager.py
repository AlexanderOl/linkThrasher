import os
from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse

from urllib3 import exceptions, disable_warnings
from bs4 import BeautifulSoup

from Managers.CacheManager import CacheManager
from Common.RequestHandler import RequestHandler
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Common.ThreadManager import ThreadManager
from Managers.XssManager import XssManager
from Models.FormRequestDTO import FormDetailsDTO, FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Tools.EyeWitness import EyeWitness


class FastUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._request_handler = RequestHandler(cookies='', headers=headers)
        disable_warnings(exceptions.InsecureRequestWarning)
        self._target_file_path = 'Targets/fast_urls.txt'
        self._res_500_error_key_path = 'Results/500_error_keys.json'
        self._res_500_error_urls_path = 'Results/500_error_urls.txt'

    def run(self):
        while True:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: FU starts...')
            result = self.__process_targets()
            if not result:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: FU finished...')
                break
            all_file_path = 'Targets/all_fast_urls.txt'
            if os.path.exists(all_file_path):
                target_urls = []
                can_add_targets = False
                with open(all_file_path) as infile:
                    for line in infile:
                        if can_add_targets:
                            target_urls.append(line.strip())
                        if len(target_urls) > 500:
                            break
                        if result == line.strip():
                            can_add_targets = True
                infile.close()

                with open(self._target_file_path, "w") as txt_file:
                    for line in target_urls:
                        txt_file.write(f"{line}\n")
                txt_file.close()
            else:
                print(f'FU stopped. {all_file_path} is missing')
                break

    def __process_targets(self):

        if os.path.exists(self._target_file_path):
            raw_urls = list(line.strip() for line in open(self._target_file_path))
            if len(raw_urls) == 0:
                print(f'No fast urls found - {self._target_file_path}')
                return
            parsed_parts = urlparse(raw_urls[len(raw_urls) - 1])
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

            errors = sqli_manager.errors_500 + ssti_manager.errors_500
            err_count = self.__store_errors(errors)
            print(f'Added {err_count} unique errors')

            last_url = raw_urls[len(raw_urls) - 1]
            print(f'Last URL was processed - {last_url}')
            return raw_urls[len(raw_urls) - 1]
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._target_file_path} is missing')
            return

    def __store_errors(self, errors):
        if len(errors) == 0:
            return 0

        checked_key_urls = {}
        for error in errors:
            url = error['url']
            netloc = urlparse(url).netloc
            response_length = len(error['response'].text)
            key = f'{netloc};{response_length}'
            if key in checked_key_urls:
                continue
            else:
                checked_key_urls[key] = url

        if not os.path.exists(self._res_500_error_key_path):
            json_file = open(self._res_500_error_key_path, 'w')
            for key in checked_key_urls.keys():
                json_file.write(f"{key}\n")
            json_file.close()
            txt_file = open(self._res_500_error_urls_path, 'w')
            for url in checked_key_urls.values():
                txt_file.write(f"{url}\n")
            txt_file.close()
            return len(checked_key_urls)
        else:
            json_file = open(self._res_500_error_key_path, 'r')
            stored_keys = json_file.readlines()
            json_file.close()
            filtered_keys = list([k_v for k_v in checked_key_urls if not f'{k_v}\n' in stored_keys])
            if len(filtered_keys) > 0:
                json_file = open(self._res_500_error_key_path, 'a')
                txt_file = open(self._res_500_error_urls_path, 'a')
                for key in filtered_keys:
                    json_file.write(f"{key}\n")
                    txt_file.write(f"{checked_key_urls[key]}\n")
                json_file.close()
                txt_file.close()
            return len(filtered_keys)

    def __get_cached_dtos(self, raw_urls: List[str], cache_key) -> Tuple[List[GetRequestDTO], List[FormRequestDTO]]:

        cache_manager = CacheManager(self._tool_name, cache_key)
        dtos = cache_manager.get_saved_result()
        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
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
            out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
            self._get_dtos = list([dto for dto in dtos['get_dtos'] if all(oos not in dto.url for oos in out_of_scope)])
            self._form_dtos = list(
                [dto for dto in dtos['form_dtos'] if all(oos not in dto.url for oos in out_of_scope)])
        return self._get_dtos, self._form_dtos

    def __check_url(self, url):
        response = self._request_handler.handle_request(url)
        if response is None:
            return
        if any(dto.response_length == len(response.text) and
               dto.status_code == response.status_code and
               urlparse(dto.url).netloc == urlparse(url).netloc
               for dto in self._get_dtos):
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
                parsed_parts = urlparse(target_url)
                if not action_tag:
                    action_tag = target_url
                elif action_tag.startswith('http'):
                    main_domain = '.'.join(parsed_parts.netloc.split('.')[-2:])
                    if main_domain not in action_tag:
                        continue
                    action_tag = action_tag
                elif action_tag.startswith('/'):
                    base_url = f'{parsed_parts.scheme}://{parsed_parts.netloc}'
                    action_tag = base_url + action_tag

                if any(form_dto for form_dto in self._form_dtos if
                       any(param for param in form_dto.form_params if param.action == action_tag)):
                    continue

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
                form_details.append(FormDetailsDTO(action_tag.strip(), params, method))
            return FormRequestDTO(target_url, form_details, dto.status_code, dto.response_length)
