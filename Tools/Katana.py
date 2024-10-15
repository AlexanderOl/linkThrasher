import os
import inject

from datetime import datetime
from typing import List
from urllib.parse import urlparse
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper
from Models.HeadRequestDTO import HeadRequestDTO


class Katana:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._head_dtos: List[HeadRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._checked_hrefs = set()
        self._max_depth = int(os.environ.get('max_depth'))
        self._cookie_manager = inject.instance(CookieHelper)

    def get_requests_dtos(self, start_url) -> List[HeadRequestDTO]:
        domain = urlparse(start_url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        result = cache_manager.get_saved_result()
        if result is None:
            result = self.__get_urls(domain, start_url)
            cache_manager.cache_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({domain}) {self._tool_name} found {len(result)} items')
        return result

    def __get_urls(self, domain, start_url) -> set[str]:

        raw_cookies = self._cookie_manager.get_raw_cookies(domain)

        cookie_param = ''
        if raw_cookies:
            cookie_param = f"-H 'Cookie: {raw_cookies}'"

        res_file = f'{self._tool_result_dir}/{domain.replace(":", "_")}.txt'

        command = (f"echo '{start_url}' | katana --timeout 3 -d {self._max_depth} -o {res_file} "
                   f"-jc -mrs 10000000 -kf all {cookie_param}")
        stream = os.popen(command)
        stream.read()

        href_urls = set()
        json_file = open(res_file, 'r')
        lines = json_file.readlines()
        for line in lines:
            netloc = urlparse(line).netloc
            if domain in netloc:
                href_urls.add(line)
        json_file.close()

        return href_urls
