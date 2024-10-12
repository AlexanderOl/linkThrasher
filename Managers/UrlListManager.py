import os
import inject
from datetime import date, datetime
from typing import List
from urllib.parse import urlparse
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Managers.SingleUrlManager import SingleUrlManager
from Common.ThreadManager import ThreadManager
from Models.HeadRequestDTO import HeadRequestDTO
from Tools.Nuclei import Nuclei


class UrlListManager:
    def __init__(self):
        self._out_of_scope = os.environ.get("out_of_scope")
        self._thread_man = inject.instance(ThreadManager)
        self._tool_name = self.__class__.__name__
        self._result: List[HeadRequestDTO] = []
        self._cache_keys = str(date.today())
        self._file_path = 'Targets/urls.txt'

        self._nuclei = inject.instance(Nuclei)
        self._request_handler = inject.instance(RequestHandler)
        self._single_url_man = inject.instance(SingleUrlManager)

    def run(self, urls=None):
        if urls:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: {self._tool_name} will run {len(urls)} urls')
            head_dtos: List[HeadRequestDTO] = []

            for url in urls:
                response = self._request_handler.send_head_request(url)
                if response is None:
                    continue
                head_dtos.append(HeadRequestDTO(response))

            self._nuclei.check_multiple_uls(str(date.today()), head_dtos)

            self._thread_man.run_all(self._single_url_man.do_run, head_dtos, debug_msg=self._tool_name)
        elif os.path.exists(self._file_path):

            head_dtos = self.__get_cached_dtos(self._file_path)

            self._nuclei.check_multiple_uls(str(date.today()), head_dtos)

            self._thread_man.run_all(self._single_url_man.do_run, head_dtos, debug_msg=self._tool_name)

        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{self._file_path} is missing')

    def __get_cached_dtos(self, file_path) -> List[HeadRequestDTO]:

        cache_manager = CacheHelper(self._tool_name, self._cache_keys)
        head_dtos = cache_manager.get_saved_result()
        out_of_scope = [x for x in self._out_of_scope.split(';') if x]

        if not head_dtos and not isinstance(head_dtos, List):

            raw_urls = list(set(line.strip() for line in open(file_path)))
            urls = set()
            for url in raw_urls:
                parsed_parts = urlparse(url)
                combined = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'
                if combined.rstrip('//') != url and combined != url:
                    urls.add(url)
                urls.add(combined)

            filtered_urls = [url for url in urls if all(oos not in url for oos in out_of_scope)]

            self._thread_man .run_all(self.__send_request, filtered_urls, debug_msg=self._tool_name)

            cache_manager.cache_result(self._result)
            head_dtos = self._result
        else:
            out_of_scope = [x for x in self._out_of_scope.split(';') if x]
            filtered_urls = list([dto for dto in head_dtos if all(oos not in dto.url for oos in out_of_scope)])
            head_dtos = filtered_urls
        return head_dtos

    def __send_request(self, url: str):
        response = self._request_handler.send_head_request(url)
        if response is None:
            return
        self._result.append(HeadRequestDTO(response))
