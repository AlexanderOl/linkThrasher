import os
from datetime import datetime

from urllib.parse import urlparse
from urllib3 import exceptions, disable_warnings

from Common.S500Handler import S500Handler
from Managers.CookieManager import CookieManager
from Managers.ManualTesting import ManualTesting
from Managers.Spider import Spider
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Tools.Feroxbuster import Feroxbuster
from Tools.Gobuster import Gobuster
from Tools.Hakrawler import Hakrawler
from Managers.XssManager import XssManager
from Models.GetRequestDTO import GetRequestDTO
from Tools.Katana import Katana
from Tools.Nuclei import Nuclei


class SingleUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self._ngrok_url = os.environ.get('ngrok_url')
        self._max_depth = os.environ.get('max_depth')
        self._check_mode = os.environ.get('check_mode')
        disable_warnings(exceptions.InsecureRequestWarning)

    def run(self, get_dto: GetRequestDTO):

        if 404 <= get_dto.status_code < 500:
            return

        start_url = get_dto.url
        domain = urlparse(start_url).netloc

        main_domain = '.'.join(domain.split('.')[-2:])

        cookie_manager = CookieManager(main_domain)
        raw_cookies = cookie_manager.get_raw_cookies()
        cookies = cookie_manager.get_cookies_dict(raw_cookies)

        gobuster = Gobuster(domain, self._headers, raw_cookies)
        gobuster.check_single_url(start_url)

        if self._check_mode == 'U':
            nuclei = Nuclei(domain, self._headers, raw_cookies)
            nuclei.check_single_url(start_url)

        hakrawler = Hakrawler(domain, raw_cookies, self._headers, cookies)
        get_hakrawler_dtos = hakrawler.get_requests_dtos(start_url)
        # get_hakrawler_dtos = []
        katana = Katana(domain, raw_cookies, self._headers, cookies)
        katana_katana_dtos = katana.get_requests_dtos(start_url)
        # katana_katana_dtos = []

        spider = Spider(domain, cookies, self._headers, self._max_depth, main_domain)
        get_spider_dtos, form_dtos = spider.get_all_links(start_url)

        get_hakrawler_dtos.extend(get_spider_dtos)
        get_hakrawler_dtos.extend(katana_katana_dtos)

        feroxbuster = Feroxbuster(domain, cookies, self._headers, raw_cookies)
        all_get_dtos, all_form_dtos = feroxbuster.check_single_url(start_url, get_hakrawler_dtos, form_dtos)

        manual_testing = ManualTesting(domain)
        get_dtos = manual_testing.save_urls_for_manual_testing(all_get_dtos, all_form_dtos)

        if len(get_dtos) == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] ({domain}) request DTOs not found')
            return
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] ({domain}) will run {len(get_dtos)} dtos')

        xss_manager = XssManager(domain, self._headers, cookies)
        xss_manager.check_get_requests(get_dtos)
        xss_manager.check_form_requests(form_dtos)

        ssrf_manager = SsrfManager(domain, cookies, self._headers)
        ssrf_manager.check_get_requests(get_dtos)
        ssrf_manager.check_form_requests(form_dtos)

        sqli_manager = SqliManager(domain, cookies, self._headers)
        sqli_manager.check_get_requests(get_dtos)
        sqli_manager.check_form_requests(form_dtos)

        ssti_manager = SstiManager(domain, cookies, self._headers)
        ssti_manager.check_get_requests(get_dtos)
        ssti_manager.check_form_requests(form_dtos)

        errors = sqli_manager.errors_500 + ssti_manager.errors_500
        s500 = S500Handler()
        s500.save_server_errors(errors)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager done with ({start_url})')
