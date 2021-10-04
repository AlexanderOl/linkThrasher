import json

import requests
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO

headers_without_delay = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
}


class LinksManager:
    def __init__(self, domain, cookies, headers):
        self.domain = domain
        self.cookies = cookies
        self.headers = headers
        self.max_depth = 2
        self.social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "cdn-cgi", "intercom", "atlassian", "instagram", "github"]
        self.checked_urls = []
        self.checked_hrefs = []
        self.checked_parsed_pathes = []
        self.urls_in_queue = []
        self.urls_counter = 0
        self.url_ext_regex = re.compile('\.jpg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.ashx$', re.IGNORECASE)

    def get_all_links(self, start_url) -> List[GetRequestDTO]:
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: LinksManager started...')

        cache_manager = CacheManager('LinksManagerResult', self.domain)
        result = cache_manager.get_saved_result()

        if not result:
            current_depth = 0
            result: List[GetRequestDTO] = []
            self.recursive_search(result, start_url, current_depth)
            cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: LinksManager found {len(result)} items')
        return result

    def check_delay(self, target_url):
        response_without_delay = requests.get(target_url, headers=headers_without_delay, cookies=self.cookies)
        if response_without_delay.elapsed.total_seconds() < 5:
            print(f'Delay found - {target_url}')

    def recursive_search(self, result, target_url, current_depth):

        if current_depth >= self.max_depth:
            return

        target_url = self.check_target_url(target_url)
        if not target_url:
            return

        try:
            print(f'Current url - {target_url}')
            response = requests.get(target_url, headers=self.headers, cookies=self.cookies)
            if response.elapsed.total_seconds() >= 5:
                self.check_delay(target_url)

            if response.status_code == 200:
                web_page = response.text
                result.append(GetRequestDTO(target_url, web_page))
            elif response.status_code == 302:
                print(f"Not OK - {target_url}, Code - {response.status_code}")
                return
            else:
                print(f"Not OK - {target_url}, Code - {response.status_code}")
                return
        except requests.exceptions.SSLError:
            target_url = target_url.replace('https', 'http')
            self.recursive_search(result, target_url, current_depth)
            return
        except Exception as inst:
            print(inst)
            print("ERROR - " + target_url)
            return

        current_depth = current_depth + 1

        href_list = self.get_href_list(web_page, target_url)

        for item in href_list:
            self.recursive_search(result, item, current_depth)

    def check_href(self, href, target_url):
        result = False
        if href:
            if '#' in href:
                href = href[1:]
            if len(href) > 2 \
                    and href not in self.social_media \
                    and href not in self.checked_hrefs \
                    and target_url[len(target_url) - len(href):] != href \
                    and (href[0] == '/' or str(href[0:4]) == "http") \
                    and href not in target_url:
                result = True

        if result:
            for current_href in self.checked_hrefs:
                words = zip(href, current_href)
                incorrect = len([c for c, d in words if c != d])
                if incorrect <= 3 and abs(len(href)-len(current_href)) <= 3:
                    return False
            self.checked_hrefs.append(href)

        return result

    def check_target_url(self, url):

        if url.endswith('/'):
            url = url[:-1]

        parsed = urlparse(url)
        if url in self.checked_urls \
                or parsed.path in self.checked_parsed_pathes \
                or any(word in url for word in self.social_media) \
                or self.domain not in parsed.netloc \
                or self.url_ext_regex.search(parsed.path):
            return

        self.checked_parsed_pathes.append(parsed.path)
        self.checked_urls.append(url)

        return url

    def get_href_list(self, web_page, target_url):
        href_list = []
        links = BeautifulSoup(web_page, "html.parser").findAll('a')
        url_parts = urlparse(target_url)
        main_url = f"{url_parts.scheme}://{url_parts.hostname}"
        for link in links:
            try:
                href = link.get('href')
                is_valid_href = self.check_href(href, target_url)
                if is_valid_href:
                    if href[0] == '/':
                        href_list.append(main_url + href)
                    elif str(href[0:4]) == "http":
                        href_list.append(href)
            except Exception as inst:
                print(inst)
        return href_list
