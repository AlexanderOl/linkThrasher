from typing import List

from tldextract import tldextract

from Managers.CookieManager import CookieManager
from Managers.FormRequestFetcher import FormRequestFetcher
from Managers.LinksManager import LinksManager
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Managers.XssManager import XssManager


class MainFlowManager:
    def __init__(self, ngrok_url, max_depth, download_path, headers):
        self.ngrok_url = ngrok_url
        self.max_depth = max_depth
        self.download_path = download_path
        self.headers = headers

    def run_main_flow(self, start_url: str, raw_cookies):
        domain_parts = tldextract.extract(start_url)
        domain = f'{domain_parts.domain}.{domain_parts.suffix}'

        cookie_manager = CookieManager(domain, self.download_path)
        if not raw_cookies:
            raw_cookies = cookie_manager.get_raw_cookies()
        cookies_dict = cookie_manager.get_cookies_dict(raw_cookies)

        subdomain_part = ''
        if domain_parts.subdomain:
            subdomain_part = f'{domain_parts.subdomain}.'
        domain = f'{subdomain_part}{domain}'

        # hakrawler = Hakrawler(domain, raw_cookie)
        # get_dtos = hakrawler.get_requests_dtos(start_url)

        links_manager = LinksManager(domain, cookies_dict, self.headers, self.max_depth)
        get_dtos = links_manager.get_all_links(start_url)

        if get_dtos is None:
            print(f'{domain} get DTOs not found')
            return

        post_manager = FormRequestFetcher(domain)
        post_dtos = post_manager.get_all_post_requests(get_dtos)

        # xss_manager = XssManager(domain, cookies_dict, self.headers)
        # xss_manager.check_get_requests(get_dtos)
        # xss_manager.check_form_requests(post_dtos)
        #
        # ssrf_manager = SsrfManager(domain, cookies_dict, self.headers, self.ngrok_url)
        # ssrf_manager.check_get_requests(get_dtos)
        # ssrf_manager.check_form_requests(post_dtos)

        sqli_manager = SqliManager(domain, cookies_dict, self.headers)
        sqli_manager.check_get_requests(get_dtos)

        ssti_manager = SstiManager(domain, cookies_dict, self.headers)
        ssti_manager.check_get_requests(get_dtos)
        ssti_manager.check_form_requests(post_dtos)
