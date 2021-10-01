import os
import pickle
import re
import requests
import tldextract
from typing import List
from datetime import datetime

from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO

_social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "cdn-cgi", "intercom", "atlassian"]


class Hakrawler:
    def __init__(self, domain, raw_cookies):
        self.domain = domain
        self.raw_cookies = raw_cookies

    def get_requests_dtos(self, start_url):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Hakrawler started...')

        cacheManager = CacheManager('HakrawlerResult', self.domain)
        result = cacheManager.get_saved_result()
        if result is None:
            result = self.get_urls(start_url)
            cacheManager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Hakrawler found {len(result)} items')
        return result

    def get_urls(self, start_url):
        cookie_param = ''
        if self.raw_cookies:
            cookie_param = f"-cookie '{self.raw_cookies}'"
        command = f"cd /root/Desktop/TOOLs/hakrawler/ | ~/go/bin/hakrawler -url {start_url} -depth 5 {cookie_param} |  grep -Eo '(http|https)://[^\"]+'"

        stream = os.popen(command)
        bash_outputs = stream.readlines()
        found_urls = [self.start_url]
        for output in bash_outputs:
            if output.endswith('\n'):
                output = output[:-1]
            if not any(word in output for word in _social_media):
                found_urls.append(output)

        regex = re.compile('\.jpg$|\.gif$|\.png$|\.js$|\.js\?', re.IGNORECASE)
        found_urls = list(filter(lambda url: not regex.search(url), found_urls))
        found_urls = list(dict.fromkeys(found_urls))

        result: List[GetRequestDTO] = []
        for item in found_urls:
            response = requests.get(item)
            if response.status_code == 200:
                result.append(GetRequestDTO(item, response.text))

        return result
