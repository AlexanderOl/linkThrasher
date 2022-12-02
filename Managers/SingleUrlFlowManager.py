import os
from datetime import datetime

import urllib3
from tldextract import tldextract
from Managers.CookieManager import CookieManager
from Managers.FormHtmlFetcher import FormRequestFetcher
from Managers.LinksManager import LinksManager
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Managers.Tools.Dirb import Dirb
from Managers.XssManager import XssManager


class SingleUrlFlowManager:
    def __init__(self, headers):
        self.ngrok_url = os.environ.get('ngrok_url')
        self.max_depth = os.environ.get('max_depth')
        self.download_path = os.environ.get('download_path')
        self.headers = headers
        self.raw_cookies = os.environ.get('raw_cookies')
        self.main_domain = os.environ.get('domain')

    def run(self, start_url: str):
        domain_parts = tldextract.extract(start_url)
        domain = f'{domain_parts.subdomain}.{domain_parts.domain}.{domain_parts.suffix}'
        if domain[0] == '.':
            domain = domain[1:]

        # dirb = Dirb(domain)
        # dirb.check_single_url(start_url)

        cookie_manager = CookieManager(self.main_domain, self.download_path)
        if not self.raw_cookies:
            raw_cookies = cookie_manager.get_raw_cookies()
        cookies_dict = cookie_manager.get_cookies_dict(raw_cookies)

        # hakrawler = Hakrawler(__domain, raw_cookie)
        # get_dtos = hakrawler.get_requests_dtos(start_url)

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        links_manager = LinksManager(domain, cookies_dict, self.headers, self.max_depth, self.main_domain)
        get_dtos = links_manager.get_all_links(start_url)

        if get_dtos is None:
            print(f'{domain} get DTOs not found')
            return

        post_manager = FormRequestFetcher(domain)
        post_dtos = post_manager.get_all_post_requests(get_dtos)

        xss_manager = XssManager(domain, cookies_dict, self.headers)
        xss_manager.check_get_requests(get_dtos)
        xss_manager.check_form_requests(post_dtos)

        ssrf_manager = SsrfManager(domain, cookies_dict, self.headers, self.ngrok_url)
        ssrf_manager.check_get_requests(get_dtos)
        ssrf_manager.check_form_requests(post_dtos)

        sqli_manager = SqliManager(domain, cookies_dict, self.headers)
        sqli_manager.check_get_requests(get_dtos)

        ssti_manager = SstiManager(domain, cookies_dict, self.headers)
        ssti_manager.check_get_requests(get_dtos)
        ssti_manager.check_form_requests(post_dtos)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: SingleUrlFlowManager done with ({start_url})')
