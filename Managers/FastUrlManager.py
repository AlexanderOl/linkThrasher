import os
import inject

from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse
from Common.Logger import Logger
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
    def __init__(self):

        self._tool_name = self.__class__.__name__
        self._out_of_scope = os.environ.get("out_of_scope")
        self._severity = int(os.environ.get("severity"))
        self._fast_urls_size = int(os.environ.get("fast_urls_size"))
        self._target_file_path = 'Targets/fast_urls.txt'
        self._all_file_path = 'Targets/all_fast_urls.txt'
        self._res_500_error_key_path = 'Results/500_error_keys.json'
        self._res_500_error_urls_path = 'Results/500_error_urls.txt'

        self._logger = inject.instance(Logger)
        self._nuclei = inject.instance(Nuclei)
        self._lfi_manager = inject.instance(LfiManager)
        self._xss_manager = inject.instance(XssManager)
        self._sqli_manager = inject.instance(SqliManager)
        self._ssrf_manager = inject.instance(SsrfManager)
        self._ssti_manager = inject.instance(SstiManager)
        self._request_handler = inject.instance(RequestHandler)
        self._request_checker = inject.instance(RequestChecker)
        self._s500 = inject.instance(S500Handler)
        self._thread_manager = inject.instance(ThreadManager)

    def run(self):
        while True:
            self._logger.log_info(f'[{datetime.now().strftime("%H:%M:%S")}]: FU starts...')
            result = self.__process_targets()
            if not result:
                self._logger.log_info(f'[{datetime.now().strftime("%H:%M:%S")}]: FU finished...')
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
                self._logger.log_info(f'FU stopped. {self._all_file_path} is missing')
                break

    def __process_targets(self):

        if os.path.exists(self._target_file_path):
            raw_urls = list(line.strip() for line in open(self._target_file_path))
            if len(raw_urls) == 0:
                self._logger.log_info(f'No fast urls found - {self._target_file_path}')
                return
            parsed_parts = urlparse(raw_urls[len(raw_urls) - 1])
            domain = parsed_parts.netloc
            head_dtos, form_dtos = self.__get_cached_dtos(raw_urls, domain)

            self._nuclei.fuzz_batch(domain, head_dtos)

            if self._severity == 1:
                self._xss_manager.check_get_requests(domain, head_dtos)
                self._xss_manager.check_form_requests(domain, form_dtos)

                self._ssrf_manager.check_get_requests(domain, head_dtos)
                self._ssrf_manager.check_form_requests(domain, form_dtos)

            self._lfi_manager.check_get_requests(domain, head_dtos)
            self._lfi_manager.check_form_requests(domain, form_dtos)

            self._sqli_manager.check_get_requests(domain, head_dtos)
            self._sqli_manager.check_form_requests(domain, form_dtos)

            self._ssti_manager.check_get_requests(domain, head_dtos)
            self._ssti_manager.check_form_requests(domain, form_dtos)

            errors = self._sqli_manager.errors_500 + self._ssti_manager.errors_500
            self._s500.save_server_errors(errors)

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
        out_of_scope = [x for x in self._out_of_scope.split(';') if x]
        self._get_dtos: List[GetRequestDTO] = []
        self._head_dtos: List[HeadRequestDTO] = []
        self._form_dtos: List[FormRequestDTO] = []

        if not dtos and not isinstance(dtos, List):

            filtered_urls = [url for url in raw_urls if all(oos not in url for oos in out_of_scope)]

            self._thread_manager.run_all(self.__check_url, filtered_urls, debug_msg='check_url')

            cache_manager.cache_result({head_key: self._head_dtos, form_key: self._form_dtos},
                                       cleanup_prev_results=True)
        else:
            out_of_scope = set([x for x in self._out_of_scope.split(';') if x])
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
