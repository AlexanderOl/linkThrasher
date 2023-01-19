import os
from typing import List
from urllib.parse import urlparse

import urllib3

from Managers.RequestHandler import RequestHandler
from Managers.SingleUrlFlowManager import SingleUrlFlowManager
from Managers.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO


class MultipleUrlFlowManager:
    def __init__(self, headers):
        self._headers = headers
        self._out_of_scope_urls = os.environ.get("out_of_scope_urls")
        self._request_handler = RequestHandler(cookies='', headers=headers)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def run(self):
        file_path = 'Targets/urls.txt'
        if os.path.exists(file_path):
            raw_urls = list(set(line.strip() for line in open(file_path)))
            urls = set()
            for url in raw_urls:
                parsed_parts = urlparse(url)
                combined = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'
                if combined != url:
                    urls.add(url)
                urls.add(combined)

            out_of_scope = self._out_of_scope_urls.split(';')
            filtered_urls = set(filter(lambda o: o not in out_of_scope, urls))

            get_dtos: List[GetRequestDTO] = []
            for url in filtered_urls:
                response = self._request_handler.handle_request(url)
                if response is None:
                    continue
                get_dtos.append(GetRequestDTO(url, response))

            single_url_man = SingleUrlFlowManager(self._headers)
            thread_man = ThreadManager()
            thread_man.run_all(single_url_man.run, get_dtos)

        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')
