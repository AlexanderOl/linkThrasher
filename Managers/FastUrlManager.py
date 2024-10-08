import os
from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse
from urllib3 import exceptions, disable_warnings

from Common.RequestChecker import RequestChecker
from Common.S500Handler import S500Handler
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Helpers.LfiManager import LfiManager
from Helpers.SqliManager import SqliManager
from Helpers.SsrfManager import SsrfManager
from Helpers.SstiManager import SstiManager
from Common.ThreadManager import ThreadManager
from Helpers.XssManager import XssManager
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Tools.Nuclei import Nuclei


class FastUrlManager:
    def __init__(self, headers):
        self._headers = headers
        self._tool_name = self.__class__.__name__
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._severity = int(os.environ.get("severity"))
        self._fast_urls_size = int(os.environ.get("fast_urls_size"))
        self._request_handler = RequestHandler(headers=headers)
        disable_warnings(exceptions.InsecureRequestWarning)
        self._target_file_path = 'Targets/fast_urls.txt'
        self._all_file_path = 'Targets/all_fast_urls.txt'
        self._res_500_error_key_path = 'Results/500_error_keys.json'
        self._res_500_error_urls_path = 'Results/500_error_urls.txt'
        self._request_checker = RequestChecker()

    def run(self):
        while True:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: FU starts...')
            result = self.__process_targets()
            if not result:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: FU finished...')
                break

            if os.path.exists(self._all_file_path):
                target_urls = []
                can_add_targets = False
                with open(self._all_file_path) as infile:
                    for line in infile:
                        if can_add_targets:
                            target_urls.append(line.strip())
                        if len(target_urls) > self._fast_urls_size:
                            break
                        if result == line.strip():
                            can_add_targets = True
                infile.close()

                with open(self._target_file_path, "w") as txt_file:
                    for line in target_urls:
                        txt_file.write(f"{line}\n")
                txt_file.close()
            else:
                print(f'FU stopped. {self._all_file_path} is missing')
                break

    def __process_targets(self):

        if os.path.exists(self._target_file_path):
            raw_urls = list(line.strip() for line in open(self._target_file_path))
            if len(raw_urls) == 0:
                print(f'No fast urls found - {self._target_file_path}')
                return
            parsed_parts = urlparse(raw_urls[len(raw_urls) - 1])
            cache_key = parsed_parts.netloc
            head_dtos, form_dtos = self.__get_cached_dtos(raw_urls, cache_key)

            nuclei = Nuclei(cache_key, self._headers)
            nuclei.fuzz_batch(head_dtos)

            if self._severity == 1:
                xss_manager = XssManager(cache_key, self._request_handler)
                xss_manager.check_get_requests(head_dtos)
                xss_manager.check_form_requests(form_dtos)

                ssrf_manager = SsrfManager(cache_key, self._request_handler)
                ssrf_manager.check_get_requests(head_dtos)
                ssrf_manager.check_form_requests(form_dtos)

            lfi_manager = LfiManager(cache_key, self._request_handler)
            lfi_manager.check_get_requests(head_dtos)
            lfi_manager.check_form_requests(form_dtos)

            sqli_manager = SqliManager(cache_key, self._request_handler)
            sqli_manager.check_get_requests(head_dtos)
            sqli_manager.check_form_requests(form_dtos)

            ssti_manager = SstiManager(cache_key, self._request_handler)
            ssti_manager.check_get_requests(head_dtos)
            ssti_manager.check_form_requests(form_dtos)

            # errors = sqli_manager.errors_500
            errors = sqli_manager.errors_500 + ssti_manager.errors_500
            s500 = S500Handler()
            s500.save_server_errors(errors)

            last_url = raw_urls[len(raw_urls) - 1]
            print(f'Last URL was processed - {last_url}')
            return last_url
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._target_file_path} is missing')
            return

    def __get_cached_dtos(self, raw_urls: List[str], cache_key) -> Tuple[List[HeadRequestDTO], List[FormRequestDTO]]:

        head_key = 'head_dtos'
        form_key = 'form_dtos'
        cache_manager = CacheHelper(self._tool_name, cache_key)
        dtos = cache_manager.get_saved_result()
        out_of_scope = [x for x in self._out_of_scope_urls.split(';') if x]
        self._get_dtos: List[GetRequestDTO] = []
        self._head_dtos: List[HeadRequestDTO] = []
        self._form_dtos: List[FormRequestDTO] = []

        if not dtos and not isinstance(dtos, List):

            filtered_urls = [url for url in raw_urls if all(oos not in url for oos in out_of_scope)]

            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url, filtered_urls, debug_msg='check_url')

            cache_manager.cache_result({head_key: self._head_dtos, form_key: self._form_dtos},
                                       cleanup_prev_results=True)
        else:
            out_of_scope = set([x for x in self._out_of_scope_urls.split(';') if x])
            self._head_dtos = list([dto for dto in dtos[head_key]
                                    if all(oos not in dto.url for oos in out_of_scope)])
            self._form_dtos = list(
                [dto for dto in dtos[form_key] if all(oos not in dto.url for oos in out_of_scope)])

        print(
            f'[{datetime.now().strftime("%H:%M:%S")}]: FastUrlFlowManager found '
            f'{len(self._head_dtos)} head_dtos and {len(self._form_dtos)} form_dtos')
        return self._head_dtos, self._form_dtos

    def __check_url(self, url: str):

        head_response = self._request_handler.send_head_request(url)
        if not head_response:
            return

        response = self._request_handler.handle_request(url, timeout=3)
        if response is None:
            return

        if len(response.text) > 1000000:
            print(f'Url ({url}) response too long')
            return

        if any(dto.response_length == len(response.text) and
               dto.status_code == response.status_code and
               urlparse(dto.url).netloc == urlparse(url).netloc
               for dto in self._get_dtos):
            return

        get_dto = GetRequestDTO(url, response)
        self._get_dtos.append(get_dto)
        self._head_dtos.append(HeadRequestDTO(response))
        form_dto = self._request_checker.find_forms(url, response.text, get_dto, self._form_dtos)
        if form_dto and not all(new_from_action in
                                [item.action for sublist in self._form_dtos for item in sublist.form_params]
                                for new_from_action in [form_param.action for form_param in form_dto.form_params]):
            self._form_dtos.append(form_dto)
