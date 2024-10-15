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
from Helpers.UrlChecker import UrlChecker
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

        self.ngrok_url = os.environ.get('ngrok_url')
        self.check_mode = os.environ.get('check_mode')
        self.single_url = os.environ.get('single_url')
        self._severity = int(os.environ.get('severity'))

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
        self._request_handler = inject.instance(RequestHandler)
        self._url_checker = inject.instance(UrlChecker)

    def run(self):
        response = self._request_handler.send_head_request(self.single_url)
        self.do_run(response)

    def do_run(self, head_dto: HeadRequestDTO):

        start_url = head_dto.url
        if 404 <= head_dto.status_code < 500:
            self._logger.log_info(f'SingleUrlFlowManager done with ({start_url}) - status: {head_dto.status_code}')
            return

        domain = urlparse(start_url).netloc

        self._httracker.check_single_url(start_url)

        self._gobuster.check_single_url(start_url)

        if self.check_mode == 'U':
            self._nuclei.check_single_url(start_url)

        spider_dtos = self._spider.get_all_links(start_url)

        hakrawler_lines = self._hakrawler.get_requests_dtos(start_url)

        katana_lines = self._katana.get_requests_dtos(start_url)

        waymore_lines = self._waymore.get_requests_dtos(start_url)

        waybackurls_lines = self._waybackurls.get_requests_dtos(start_url)

        feroxbuster_lines = self._feroxbuster.check_single_url(start_url)

        all_lines = set()
        all_lines.update(hakrawler_lines)
        all_lines.update(katana_lines)
        all_lines.update(waymore_lines)
        all_lines.update(waybackurls_lines)
        all_lines.update(feroxbuster_lines)

        head_dtos, form_dtos = self._url_checker.filter_dtos(domain, spider_dtos, all_lines)

        self._nuclei.fuzz_batch(domain, head_dtos)

        self._manual_testing.save_urls_for_manual_testing(domain, head_dtos, form_dtos)

        if len(head_dtos) == 0:
            self._logger.log_info(f'({domain}) request DTOs not found')
            return
        else:
            self._logger.log_info(f'({domain}) will run {len(head_dtos)} heads, {len(form_dtos)} forms')

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

        if self.check_mode == 'UL':
            with open("Targets/urls.txt", "r", encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            with open("Targets/urls.txt", "w") as f:
                for line in lines:
                    if start_url.rstrip('/') not in line.strip("\n"):
                        f.write(line)

        self._logger.log_info(f'SingleUrlFlowManager done with ({start_url})')

