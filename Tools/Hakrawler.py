import os
import re
from urllib.parse import urlparse
from datetime import datetime
from typing import List

from Common.ThreadManager import ThreadManager
from Managers.CacheManager import CacheManager
from Common.RequestHandler import RequestHandler
from Tools.LinkFinder import LinkFinder
from Models.GetRequestDTO import GetRequestDTO


class Hakrawler:
    def __init__(self, domain, raw_cookies='', headers={}, cookies=''):
        self._domain = domain
        self._raw_cookies = raw_cookies
        self._max_depth = os.environ.get('max_depth')
        self._social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "intercom", "atlassian"]
        self._tool_name = self.__class__.__name__
        self._request_handler = RequestHandler(cookies, headers)
        self._url_ignore_ext_regex = re.compile(
            '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.ashx$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
            '|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.mp4$|\.avi$|\.mp3$',
            re.IGNORECASE)
        self._result: List[GetRequestDTO] = []
        self._checked_hrefs = set()

    def get_requests_dtos(self, start_url) -> List[GetRequestDTO]:
        cache_manager = CacheManager('Hakrawler', self._domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(start_url)
            cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self, start_url) -> List[GetRequestDTO]:

        cookie_param = ''
        if self._raw_cookies:
            cookie_param = f"-h 'Cookie: {self._raw_cookies}'"

        command = f"echo '{start_url}' | hakrawler -d {self._max_depth} {cookie_param} -t 20"
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
                if not any(word in output for word in self._social_media) and self._domain in output:
                    href_urls.add(output)
            elif output.startswith('[script] '):
                output = output.replace('[script] ', '')
                if not any(word in output for word in self._social_media) and self._domain in output:
                    script_urls.add(output)

        link_finder = LinkFinder(self._domain, start_url)
        get_urls_from_js = link_finder.search_urls_in_js(script_urls)
        href_urls.update(get_urls_from_js)

        tm = ThreadManager()
        tm.run_all(self.__check_href_urls, href_urls, debug_msg=self._tool_name)

        return self._result

    def __check_href_urls(self, url: str):
        url_parts = urlparse(url)
        if url_parts.path in self._checked_hrefs or self._url_ignore_ext_regex.search(url):
            return
        else:
            self._checked_hrefs.add(url_parts.path)

        response = self._request_handler.handle_request(url, timeout=5)
        if response is None:
            return

        if len(self._result) > 0 and any(dto for dto in self._result if
                                         dto.response_length == len(response.text) and
                                         dto.status_code == response.status_code):
            return

        if response.status_code < 400 or response.status_code == 500:
            self._result.append(GetRequestDTO(url, response))

        return self._result
