import os
import inject

from urllib.parse import urlparse
from Common.Logger import Logger
from Common.RequestHandler import RequestHandler
from Common.S500Handler import S500Handler
from Helpers.LfiManager import LfiManager
from Helpers.ManualTesting import ManualTesting
from Helpers.Spider import Spider
from Helpers.SqliManager import SqliManager
from Helpers.SsrfManager import SsrfManager
from Helpers.SstiManager import SstiManager
from Helpers.UrlChecker import UrlChecker
from Helpers.XssManager import XssManager
from Models.Constants import VALID_STATUSES
from Models.HeadRequestDTO import HeadRequestDTO
from Tools.Feroxbuster import Feroxbuster
from Tools.Gobuster import Gobuster
from Tools.Hakrawler import Hakrawler
from Tools.Httracker import Httracker
from Tools.Katana import Katana
from Tools.LinkFinder import LinkFinder
from Tools.Nuclei import Nuclei
from Tools.Waybackurls import Waybackurls
from Tools.Waymore import Waymore


class SingleUrlManager:
    def __init__(self):
        self._check_mode = os.environ.get('check_mode')
        self._single_url = os.environ.get('single_url')
        self._severity = int(os.environ.get('severity'))

    def run(self):
        request_handler = inject.instance(RequestHandler)
        response = request_handler.send_head_request(self._single_url)
        self.do_run(response)

    def do_run(self, head_dto: HeadRequestDTO):

        start_url = head_dto.url

        logger = inject.instance(Logger)
        if head_dto.status_code not in VALID_STATUSES:
            logger.log_warn(f'SingleUrlFlowManager done with ({start_url}) - status: {head_dto.status_code}')
            return

        domain = urlparse(start_url).netloc

        httracker = inject.instance(Httracker)
        httracker.check_single_url(start_url)

        gobuster = inject.instance(Gobuster)
        gobuster.check_single_url(start_url)

        nuclei = inject.instance(Nuclei)
        if self._check_mode == 'U':
            nuclei.check_single_url(start_url)

        spider = inject.instance(Spider)
        spider_dtos = spider.get_all_links(start_url)

        hakrawler = inject.instance(Hakrawler)
        hakrawler_lines = hakrawler.get_requests_dtos(start_url)

        katana = inject.instance(Katana)
        katana_lines = katana.get_requests_dtos(start_url)

        waymore = inject.instance(Waymore)
        waymore_lines = waymore.get_requests_dtos(start_url)

        waybackurls = inject.instance(Waybackurls)
        waybackurls_lines = waybackurls.get_requests_dtos(start_url)

        feroxbuster = inject.instance(Feroxbuster)
        feroxbuster_lines = feroxbuster.check_single_url(start_url)

        all_lines = set()
        all_lines.update(hakrawler_lines)
        all_lines.update(katana_lines)
        all_lines.update(waymore_lines)
        all_lines.update(waybackurls_lines)
        all_lines.update(feroxbuster_lines)

        link_finder = inject.instance(LinkFinder)
        get_urls_from_js = link_finder.get_urls_from_js(all_lines, start_url)
        all_lines.update(get_urls_from_js)

        url_checker = inject.instance(UrlChecker)
        head_dtos, form_dtos = url_checker.filter_dtos(domain, spider_dtos, all_lines)

        if len(head_dtos) == 0:
            logger.log_warn(f'({domain}) request DTOs not found')
            return
        else:
            logger.log_warn(f'({domain}) will run {len(head_dtos)} heads, {len(form_dtos)} forms')

        nuclei.fuzz_urls_batch(domain, head_dtos)

        manual_testing = inject.instance(ManualTesting)
        manual_testing.save_urls_for_manual_testing(domain, head_dtos, form_dtos)

        if self._severity == 1:
            xss_manager = inject.instance(XssManager)
            xss_manager.check_get_requests(domain, head_dtos)
            xss_manager.check_form_requests(domain, form_dtos)

            ssrf_manager = inject.instance(SsrfManager)
            ssrf_manager.check_get_requests(domain, head_dtos)
            ssrf_manager.check_form_requests(domain, form_dtos)

        lfi_manager = inject.instance(LfiManager)
        lfi_manager.check_get_requests(domain, head_dtos)
        lfi_manager.check_form_requests(domain, form_dtos)

        sqli_manager = inject.instance(SqliManager)
        sqli_manager.check_get_requests(domain, head_dtos)
        sqli_manager.check_form_requests(domain, form_dtos)

        ssti_manager = inject.instance(SstiManager)
        ssti_manager.check_get_requests(domain, head_dtos)
        ssti_manager.check_form_requests(domain, form_dtos)

        errors = sqli_manager.errors_500 + ssti_manager.errors_500
        s500 = inject.instance(S500Handler)
        s500.save_server_errors(errors)

        if self._check_mode == 'UL':
            with open("Targets/urls.txt", "r", encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            with open("Targets/urls.txt", "w") as f:
                for line in lines:
                    if start_url.rstrip('/') not in line.strip("\n"):
                        f.write(line)

        logger.log_warn(f'SingleUrlFlowManager done with ({start_url})')
