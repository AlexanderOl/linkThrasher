import os
import queue

import inject

from typing import List, Tuple
from urllib.parse import urlparse
from Common.RequestChecker import RequestChecker
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Helpers.CacheHelper import CacheHelper
from Models.Constants import URL_IGNORE_EXT_REGEX, VALID_STATUSES
from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class UrlChecker:

    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._out_of_scope = os.environ.get('out_of_scope')
        self._thread_manager = inject.instance(ThreadManager)
        self._request_handler = inject.instance(RequestHandler)
        self._request_checker = inject.instance(RequestChecker)
        self._checked_hrefs = set()

    def filter_dtos(self, domain: str, spider_head_dtos: List[HeadRequestDTO], lines: set[str]) \
            -> Tuple[List[HeadRequestDTO], List[FormRequestDTO]]:

        head_key = 'head_dtos'
        form_key = 'form_dtos'
        cache_manager = CacheHelper(self._tool_name, domain)

        result = cache_manager.get_saved_result()

        if not result and not isinstance(result, dict):

            if len(lines) > 1000:
                lines = self.__reduce_urls_qty(lines)

            head_queue = queue.Queue()
            self._thread_manager.run_all(self.__check_urls, lines, debug_msg=f'({domain}): Urls checking',
                                         args2=head_queue)

            head_dtos = list(head_queue.queue)

            out_of_scope = [x for x in self._out_of_scope.split(';') if x]
            checked_keys = set([dto.key for dto in head_dtos])

            for dto in spider_head_dtos:
                if dto.key not in checked_keys and all(oos not in urlparse(dto.url).netloc for oos in out_of_scope):
                    checked_keys.add(dto.key)
                    head_dtos.append(dto)

            filtered_urls = [dto.url for dto in head_dtos if not urlparse(dto.url).path.endswith('.js')]

            get_queue = queue.Queue()
            form_queue = queue.Queue()
            queues = (get_queue, form_queue)

            self._thread_manager.run_all(self.__get_forms, filtered_urls, debug_msg=f'({domain}): Forms searching',
                                         args2=queues)

            form_dtos = list(queues[1].queue)
            cache_manager.cache_result({head_key: head_dtos, form_key: form_dtos})
        else:
            head_dtos = result[head_key]
            form_dtos = result[form_key]

        return head_dtos, form_dtos

    def __get_forms(self, url: str, queues: Tuple[queue, queue]):

        response = self._request_handler.handle_request(url, timeout=3)
        if response is None:
            return

        get_dtos = list(queues[1].queue)
        if any(dto.response_length == len(response.text) and
               dto.status_code == response.status_code and
               urlparse(dto.url).netloc == urlparse(url).netloc
               for dto in get_dtos):
            return

        get_dto = GetRequestDTO(url, response)
        queues[0].put(get_dto)

        form_dtos = list(queues[1].queue)

        form_dto = self._request_checker.find_forms(url, response.text, get_dto, form_dtos)
        if form_dto and not all(form_dto.key != dto.key for dto in form_dtos):
            queues[1].put.append(form_dto)

    def __check_urls(self, url: str, result_queue: queue):

        parsed_url = urlparse(url)
        key = self._request_checker.get_url_key(url)
        if key in self._checked_hrefs or URL_IGNORE_EXT_REGEX.search(parsed_url.path):
            return
        self._checked_hrefs.add(key)

        check = self._request_handler.send_head_request(url)
        if check is None:
            return

        response = self._request_handler.send_head_request(url, timeout=3)
        if response is None:
            return

        if response.status_code in VALID_STATUSES and parsed_url.netloc == urlparse(response.url).netloc:
            result_queue.put(HeadRequestDTO(response))

    def __reduce_urls_qty(self, lines):
        filtered = set()
        checked_keys = set()
        for line in lines:
            parsed_parts = urlparse(line)
            key = ''
            if '?' in line:
                params = parsed_parts.query.split('&')
                for param in params:
                    split = param.split('=')
                    key += split[0]
            else:
                split_path = parsed_parts.path.split('/')
                for part in split_path:
                    if part.isdigit():
                        key += 'numb'
                    elif self._request_checker.is_valid_hash(part):
                        key += 'guid'
                    elif self._request_checker.is_date(part):
                        key += 'date'
                    else:
                        key += '_'
            if key not in checked_keys:
                filtered.add(line)
                checked_keys.add(key)

        return filtered
