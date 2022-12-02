import os
import re
import requests
from datetime import datetime
from typing import List
from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO


class Hakrawler:
    def __init__(self, domain, raw_cookies):
        self.__domain = domain
        self.__raw_cookies = raw_cookies
        self.__social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "cdn-cgi", "intercom", "atlassian"]
        self.__tool_name = self.__class__.__name__

    def get_requests_dtos(self, start_url) -> List[GetRequestDTO]:
        cache_manager = CacheManager('Hakrawler', self.__domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(start_url)
            cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(result)} items')
        return result

    def __get_urls(self, start_url) -> List[GetRequestDTO]:
        cookie_param = ''
        if self.__raw_cookies:
            cookie_param = f"-cookie '{self.__raw_cookies}'"
        command = f"cd /root/Desktop/TOOLs/hakrawler/ | " \
                  f"~/go/bin/hakrawler -url {start_url} -depth 5 {cookie_param} |  " \
                  f"grep -Eo '(http|https)://[^\"]+'"

        stream = os.popen(command)
        bash_outputs = stream.readlines()
        found_urls = [self.start_url]
        for output in bash_outputs:
            if output.endswith('\n'):
                output = output[:-1]
            if not any(word in output for word in self.__social_media):
                found_urls.append(output)

        regex = re.compile('\.jpg$|\.gif$|\.png$|\.js$|\.js\?', re.IGNORECASE)
        found_urls = list(filter(lambda url: not regex.search(url), found_urls))
        found_urls = list(dict.fromkeys(found_urls))

        result: List[GetRequestDTO] = []
        for item in found_urls:
            response = requests.get(item)
            if response.status_code == 200:
                result.append(GetRequestDTO(item, response.text, response.status_code))

        return result
