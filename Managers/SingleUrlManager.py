import os
import inject

from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse
from Common.Logger import Logger
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.S500Handler import S500Handler
from Common.ThreadManager import ThreadManager
from Helpers.LfiManager import LfiManager
from Helpers.ManualTesting import ManualTesting
from Helpers.Spider import Spider
from Helpers.SqliManager import SqliManager
from Helpers.SsrfManager import SsrfManager
from Helpers.SstiManager import SstiManager
from Helpers.XssManager import XssManager
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Tools.Feroxbuster import Feroxbuster
from Tools.Gobuster import Gobuster
from Tools.Hakrawler import Hakrawler
from Tools.Httracker import Httracker
from Tools.Katana import Katana
from Tools.Nuclei import Nuclei
from Tools.Waybackurls import Waybackurls
from Tools.Waymore import Waymore


class SingleUrlManager:
    def __init__(self):
        super().__init__()
        self.ngrok_url = os.environ.get('ngrok_url')
        self.check_mode = os.environ.get('check_mode')
        self.single_url = os.environ.get('single_url')
        self.severity = int(os.environ.get('severity'))
        self.out_of_scope = os.environ.get("out_of_scope")

        self._s500 = inject.instance(S500Handler)
        self._katana = inject.instance(Katana)
        self._spider = inject.instance(Spider)
        self._waybackurls = inject.instance(Waybackurls)
        self._waymore = inject.instance(Waymore)
        self._hakrawler = inject.instance(Hakrawler)
        self._feroxbuster = inject.instance(Feroxbuster)
        self._lfi_manager = inject.instance(LfiManager)
        self._xss_manager = inject.instance(XssManager)
        self._sqli_manager = inject.instance(SqliManager)
        self._ssrf_manager = inject.instance(SsrfManager)
        self._ssti_manager = inject.instance(SstiManager)
        self._gobuster = inject.instance(Gobuster)
        self._httracker = inject.instance(Httracker)
        self._logger = inject.instance(Logger)
        self._nuclei = inject.instance(Nuclei)
        self._manual_testing = inject.instance(ManualTesting)
        self._thread_manager = inject.instance(ThreadManager)
        self._request_handler = inject.instance(RequestHandler)
        self._request_checker = inject.instance(RequestChecker)

    def run(self):
        response = self._request_handler.send_head_request(self.single_url)
        self.do_run(response)

    def do_run(self, head_dto: HeadRequestDTO):

        start_url = head_dto.url
        if 404 <= head_dto.status_code < 500:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: '
                  f'SingleUrlFlowManager done with ({start_url}) - status: {head_dto.status_code}')
            return

        domain = urlparse(start_url).netloc

        self._httracker.check_single_url(start_url)

        self._gobuster.check_single_url(start_url)

        if self.check_mode == 'U':
            self._nuclei.check_single_url(start_url)

        all_head_dtos: List[HeadRequestDTO] = []

        get_hakrawler_dtos = self._hakrawler.get_requests_dtos(start_url)

        katana_dtos = self._katana.get_requests_dtos(start_url)

        waymore_dtos = self._waymore.get_requests_dtos(domain)

        waybackurls_dtos = self._waybackurls.get_requests_dtos(domain)

        get_spider_dtos = self._spider.get_all_links(start_url)

        get_feroxbuster_dtos = self._feroxbuster.check_single_url(start_url)

        all_head_dtos.extend(get_hakrawler_dtos)
        all_head_dtos.extend(get_spider_dtos)
        all_head_dtos.extend(katana_dtos)
        all_head_dtos.extend(waybackurls_dtos)
        all_head_dtos.extend(waymore_dtos)
        all_head_dtos.extend(get_feroxbuster_dtos)

        head_dtos, form_dtos = self.__filter_dtos(all_head_dtos)

        self._nuclei.fuzz_batch(domain, head_dtos)

        self._manual_testing.save_urls_for_manual_testing(domain, head_dtos, form_dtos)

        if len(head_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) request DTOs not found')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) will run {len(head_dtos)} dtos')

        if self.severity == 1:
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

        if self.check_mode == 'UL':
            with open("Targets/urls.txt", "r", encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            with open("Targets/urls.txt", "w") as f:
                for line in lines:
                    if start_url.rstrip('/') not in line.strip("\n"):
                        f.write(line)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager done with ({start_url})')

    def __filter_dtos(self, all_head_dtos: List[HeadRequestDTO]) -> Tuple[List[HeadRequestDTO], List[FormRequestDTO]]:

        head_dtos: List[HeadRequestDTO] = []
        self.form_dtos: List[FormRequestDTO] = []
        checked_keys = set()
        out_of_scope = [x for x in self.out_of_scope.split(';') if x]

        for dto in all_head_dtos:
            if dto.key not in checked_keys and all(oos not in dto.url for oos in out_of_scope):
                checked_keys.add(dto.key)
                head_dtos.append(dto)

        filtered_urls = [dto.url for dto in head_dtos]

        self.get_dtos: List[GetRequestDTO] = []

        self._thread_manager.run_all(self.__check_url, filtered_urls, debug_msg='forms_searching')

        return head_dtos, self.form_dtos

    def __check_url(self, url: str):

        response = self._request_handler.handle_request(url, timeout=3)
        if response is None:
            return

        if any(dto.response_length == len(response.text) and
               dto.status_code == response.status_code and
               urlparse(dto.url).netloc == urlparse(url).netloc
               for dto in self.get_dtos):
            return

        get_dto = GetRequestDTO(url, response)
        self.get_dtos.append(get_dto)
        form_dto = self._request_checker.find_forms(url, response.text, get_dto, self.form_dtos)
        if form_dto and not all(new_from_action in
                                [item.action for sublist in self.form_dtos for item in sublist.form_params]
                                for new_from_action in [form_param.action for form_param in form_dto.form_params]):
            self.form_dtos.append(form_dto)
