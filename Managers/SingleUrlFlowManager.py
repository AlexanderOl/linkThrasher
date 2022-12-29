import os
from typing import List
from urllib.parse import urlparse

import urllib3
from datetime import datetime
from tldextract import tldextract

from Managers.CookieManager import CookieManager
from Managers.ManualTesting import ManualTesting
from Managers.Spider import Spider
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Managers.Tools.Dirb import Dirb
from Managers.Tools.Gobuster import Gobuster
from Managers.Tools.Hakrawler import Hakrawler
from Managers.XssManager import XssManager
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO


class SingleUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self.ngrok_url = os.environ.get('ngrok_url')
        self.max_depth = os.environ.get('max_depth')
        self.download_path = os.environ.get('download_path')
        self.raw_cookies = os.environ.get('raw_cookies')
        self.main_domain = os.environ.get('domain')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def run(self, start_url: str):
        domain_parts = tldextract.extract(start_url)
        domain = f'{domain_parts.subdomain}.{domain_parts.domain}.{domain_parts.suffix}'
        if domain[0] == '.':
            domain = domain[1:]

        # dirb = Dirb(domain)
        # dirb.check_single_url(start_url)

        gobuster = Gobuster(domain)
        gobuster.check_single_url(start_url)

        cookie_manager = CookieManager(self.main_domain, self.download_path)

        if self.raw_cookies:
            cookies_dict = self.raw_cookies
            raw_cookies = self.raw_cookies
        else:
            raw_cookies = cookie_manager.get_raw_cookies()
            cookies_dict = cookie_manager.get_cookies_dict(raw_cookies)

        hakrawler = Hakrawler(domain, raw_cookies, self._headers, cookies_dict)
        get_hakrawler_dtos = hakrawler.get_requests_dtos(start_url)

        spider = Spider(domain, cookies_dict, self._headers, self.max_depth, self.main_domain)
        get_spider_dtos, form_dtos = spider.get_all_links(start_url)

        get_hakrawler_dtos.extend(get_spider_dtos)

        manual_testing = ManualTesting(domain)
        get_dtos = manual_testing.save_urls_for_manual_testing(get_hakrawler_dtos, form_dtos)

        if len(get_dtos) == 0:
            print(f'{domain} request DTOs not found')
            return

        xss_manager = XssManager(domain, cookies_dict, self._headers)
        xss_manager.check_get_requests(get_dtos)
        xss_manager.check_form_requests(form_dtos)

        ssrf_manager = SsrfManager(domain, cookies_dict, self._headers, self.ngrok_url)
        ssrf_manager.check_get_requests(get_dtos)
        ssrf_manager.check_form_requests(form_dtos)

        sqli_manager = SqliManager(domain, cookies_dict, self._headers)
        sqli_manager.check_get_requests(get_dtos)

        ssti_manager = SstiManager(domain, cookies_dict, self._headers)
        ssti_manager.check_get_requests(get_dtos)
        ssti_manager.check_form_requests(form_dtos)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager done with ({start_url})')


