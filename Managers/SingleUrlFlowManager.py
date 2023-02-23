import os
from datetime import datetime

import urllib3
from tldextract import tldextract

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
from Tools.Lfimap import Lfimap
from Tools.Nuclei import Nuclei


class SingleUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self._ngrok_url = os.environ.get('ngrok_url')
        self._max_depth = os.environ.get('max_depth')
        self._download_path = os.environ.get('download_path')
        self._raw_cookies = os.environ.get('raw_cookies')
        self._main_domain = os.environ.get('domain')
        self._check_mode = os.environ.get('check_mode')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def run(self, get_dto: GetRequestDTO):

        if 404 <= get_dto.status_code < 500:
            return

        start_url = get_dto.url
        domain_parts = tldextract.extract(start_url)
        domain = f'{domain_parts.subdomain}.{domain_parts.domain}.{domain_parts.suffix}'
        if domain[0] == '.':
            domain = domain[1:]
        if domain[len(domain)-1] == '.':
            domain = domain[:-1]

        gobuster = Gobuster(domain, self._headers)
        gobuster.check_single_url(start_url)

        if self._check_mode == 'U':
            nuclei = Nuclei(domain, self._headers)
            nuclei.check_single_url(start_url)

        cookie_manager = CookieManager(self._main_domain, self._download_path)
        if self._raw_cookies:
            cookies = self._raw_cookies
            raw_cookies = self._raw_cookies
        else:
            raw_cookies = cookie_manager.get_raw_cookies()
            cookies = cookie_manager.get_cookies_dict(raw_cookies)

        hakrawler = Hakrawler(domain, raw_cookies, self._headers, cookies)
        get_hakrawler_dtos = hakrawler.get_requests_dtos(start_url)
        # get_hakrawler_dtos = []

        spider = Spider(domain, cookies, self._headers, self._max_depth, self._main_domain)
        get_spider_dtos, form_dtos = spider.get_all_links(start_url)

        get_hakrawler_dtos.extend(get_spider_dtos)

        feroxbuster = Feroxbuster(domain, cookies, self._headers)
        all_get_dtos, all_form_dtos = feroxbuster.check_single_url(start_url, get_hakrawler_dtos, form_dtos)

        manual_testing = ManualTesting(domain)
        get_dtos = manual_testing.save_urls_for_manual_testing(all_get_dtos, all_form_dtos)

        lfimap = Lfimap(domain, self._headers)
        lfimap.check_dtos(get_dtos, start_url)

        if len(get_dtos) == 0:
            print(f'{domain} request DTOs not found')
            return

        xss_manager = XssManager(domain, cookies, self._headers)
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

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager done with ({start_url})')
