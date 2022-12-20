import os
import re
import requests
from datetime import datetime
from typing import List
from Managers.CacheManager import CacheManager
from Managers.Tools.LinkFinder import LinkFinder
from Models.GetRequestDTO import GetRequestDTO


class Hakrawler:
    def __init__(self, domain, raw_cookies):
        self.__domain = domain
        self.__raw_cookies = raw_cookies
        self.__social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "cdn-cgi", "intercom",
                               "atlassian"]
        self.__tool_name = self.__class__.__name__

    def get_requests_dtos(self, start_url) -> List[GetRequestDTO]:
        cache_manager = CacheManager('Hakrawler', self.__domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(start_url)
            cache_manager.save_result(result)

        print(
            f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {len(result)} items')
        return result

    def __get_urls(self, start_url) -> List[GetRequestDTO]:

        cookie_param = ''
        if self.__raw_cookies:
            cookie_param = f"-h 'Cookie: {self.__raw_cookies}'"

        command = f"echo '{start_url}' | hakrawler - d 5 {cookie_param} "
        stream = os.popen(command)
        bash_outputs = stream.readlines()
        href_urls = set()
        script_urls = set()
        for output in bash_outputs:
            if output.endswith('\n'):
                output = output[:-1]
            if output.endswith('/'):
                output = output[:-1]
            if output.startswith('[href] '):
                output = output.replace('[href] ', '')
                if not any(word in output for word in self.__social_media) and self.__domain in output:
                    href_urls.add(output)
            elif output.startswith('[script] '):
                output = output.replace('[script] ', '')
                if not any(word in output for word in self.__social_media) and self.__domain in output:
                    script_urls.add(output)

        link_finder = LinkFinder(self.__domain)
        link_finder.search_urls_in_js(script_urls)

        return self.__check_href_urls(href_urls)

    def __check_href_urls(self, href_urls):
        result: List[GetRequestDTO] = []
        for item in href_urls:
            try:
                response = requests.get(item)
                result.append(GetRequestDTO(item, response))
            except Exception as ex:
                print(f'Exception - {ex} on url - {item}')

        return result
