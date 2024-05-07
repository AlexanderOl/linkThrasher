import os
from datetime import datetime
from urllib.parse import urlparse
from urllib3 import exceptions, disable_warnings

from Common.RequestHandler import RequestHandler
from Common.S500Handler import S500Handler
from Helpers.CookieHelper import CookieHelper
from Helpers.LfiManager import LfiManager
from Helpers.ManualTesting import ManualTesting
from Helpers.Spider import Spider
from Helpers.SqliManager import SqliManager
from Helpers.SsrfManager import SsrfManager
from Helpers.SstiManager import SstiManager
from Helpers.XssManager import XssManager
from Models.HeadRequestDTO import HeadRequestDTO
from Tools.Feroxbuster import Feroxbuster
from Tools.Gobuster import Gobuster
from Tools.Hakrawler import Hakrawler
from Tools.Httracker import Httracker
from Tools.Katana import Katana
from Tools.Nuclei import Nuclei
from Tools.Waybackurls import Waybackurls


class SingleUrlManager:
    def __init__(self, headers):
        self._headers = headers
        self._ngrok_url = os.environ.get('ngrok_url')
        self._check_mode = os.environ.get('check_mode')
        self._single_url = os.environ.get('single_url')
        self._severity = int(os.environ.get('severity'))
        disable_warnings(exceptions.InsecureRequestWarning)

    def run(self):
        request_handler = RequestHandler(cookies="", headers=self._headers)
        response = request_handler.send_head_request(self._single_url)
        self.do_run(response)

    def do_run(self, head_dto: HeadRequestDTO):

        start_url = head_dto.url
        if 404 <= head_dto.status_code < 500:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: '
                  f'SingleUrlFlowManager done with ({start_url}) - status: {head_dto.status_code}')
            return

        domain = urlparse(start_url).netloc

        main_domain = '.'.join(domain.split('.')[-2:])

        cookie_manager = CookieHelper(main_domain)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)

        httracker = Httracker(domain)
        httracker.check_single_url(start_url)

        gobuster = Gobuster(domain, self._headers, raw_cookies)
        gobuster.check_single_url(start_url)

        nuclei = Nuclei(domain, self._headers, raw_cookies)
        if self._check_mode == 'U':
            nuclei.check_single_url(start_url)

        hakrawler = Hakrawler(domain, raw_cookies, self._headers, cookies)
        get_hakrawler_dtos = hakrawler.get_requests_dtos(start_url)

        katana = Katana(domain, raw_cookies, self._headers, cookies)
        katana_dtos = katana.get_requests_dtos(start_url)

        waybackurls = Waybackurls(domain, raw_cookies, self._headers, cookies)
        waybackurls_dtos = waybackurls.get_requests_dtos()

        spider = Spider(domain, cookies, self._headers, main_domain)
        get_spider_dtos, form_dtos = spider.get_all_links(start_url)

        get_hakrawler_dtos.extend(get_spider_dtos)
        get_hakrawler_dtos.extend(katana_dtos)
        get_hakrawler_dtos.extend(waybackurls_dtos)

        feroxbuster = Feroxbuster(domain, cookies, self._headers, raw_cookies)
        all_get_dtos, all_form_dtos = feroxbuster.check_single_url(start_url, get_hakrawler_dtos, form_dtos)

        nuclei.fuzz_batch(all_get_dtos)

        manual_testing = ManualTesting(domain)
        head_dtos = manual_testing.save_urls_for_manual_testing(all_get_dtos, all_form_dtos)

        if len(head_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) request DTOs not found')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) will run {len(head_dtos)} dtos')

        if self._severity == 1:
            xss_manager = XssManager(domain, headers=self._headers, cookies=cookies)
            xss_manager.check_get_requests(head_dtos)
            xss_manager.check_form_requests(all_form_dtos)

            ssrf_manager = SsrfManager(domain, headers=self._headers, cookies=cookies)
            ssrf_manager.check_get_requests(head_dtos)
            ssrf_manager.check_form_requests(all_form_dtos)

        lfi_manager = LfiManager(domain, headers=self._headers, cookies=cookies)
        lfi_manager.check_get_requests(head_dtos)
        lfi_manager.check_form_requests(form_dtos)

        sqli_manager = SqliManager(domain, headers=self._headers, cookies=cookies)
        sqli_manager.check_get_requests(head_dtos)
        sqli_manager.check_form_requests(all_form_dtos)

        ssti_manager = SstiManager(domain, headers=self._headers, cookies=cookies)
        ssti_manager.check_get_requests(head_dtos)
        ssti_manager.check_form_requests(all_form_dtos)

        errors = sqli_manager.errors_500 + ssti_manager.errors_500
        s500 = S500Handler()
        s500.save_server_errors(errors)

        if self._check_mode == 'UL':
            with open("Targets/urls.txt", "r") as f:
                lines = f.readlines()
            with open("Targets/urls.txt", "w") as f:
                for line in lines:
                    if start_url.rstrip('/') not in line.strip("\n"):
                        f.write(line)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager done with ({start_url})')
