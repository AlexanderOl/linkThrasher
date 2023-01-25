import os
import urllib3
from datetime import date
from typing import List
from urllib.parse import urlparse
from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO
from Tools.Nuclei import Nuclei


class MultipleUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._request_handler = RequestHandler(cookies='', headers=headers)
        self._tool_name = self.__class__.__name__
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def run(self):
        file_path = 'Targets/urls.txt'
        if os.path.exists(file_path):

            get_dtos = self.__get_cached_dtos(file_path)

            nuclei = Nuclei(str(date.today()))
            nuclei.check_multiple_uls(get_dtos)

            single_url_man = SingleUrlFlowManager(self._headers)
            thread_man = ThreadManager()
            thread_man.run_all(single_url_man.run, get_dtos)

        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')

    def __get_cached_dtos(self, file_path) -> List[GetRequestDTO]:

        cache_manager = CacheManager(self._tool_name, str(date.today()))
        get_dtos = cache_manager.get_saved_result()
        out_of_scope = self._out_of_scope_urls.split(';')

        if not get_dtos and not isinstance(get_dtos, List):

            raw_urls = list(set(line.strip() for line in open(file_path)))
            urls = set()
            for url in raw_urls:
                parsed_parts = urlparse(url)
                combined = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'
                if combined != url:
                    urls.add(url)
                urls.add(combined)

            filtered_urls = [url for url in urls if all(oos not in url for oos in out_of_scope)]

            get_dtos: List[GetRequestDTO] = []
            for url in filtered_urls:
                response = self._request_handler.handle_request(url)
                if response is None:
                    continue
                get_dtos.append(GetRequestDTO(url, response))

            cache_manager.save_result(get_dtos)
        else:
            out_of_scope = self._out_of_scope_urls.split(';')
            filtered_urls = list([dto for dto in get_dtos if all(oos not in dto.url for oos in out_of_scope)])
            get_dtos = filtered_urls
        return get_dtos
