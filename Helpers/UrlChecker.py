import os
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
        self._get_dtos: List[GetRequestDTO] = []
        self._head_dtos: List[HeadRequestDTO] = []
        self._form_dtos: List[FormRequestDTO] = []
        self._checked_hrefs = set()

    def filter_dtos(self, domain: str, spider_head_dtos: List[HeadRequestDTO], lines: set[str]) \
            -> Tuple[List[HeadRequestDTO], List[FormRequestDTO]]:

        head_key = 'head_dtos'
        form_key = 'form_dtos'
        cache_manager = CacheHelper(self._tool_name, domain)

        result = cache_manager.get_saved_result()

        if not result and not isinstance(result, List):

            self._thread_manager.run_all(self.__check_urls, lines, debug_msg='urls_checking')

            checked_keys = set()
            out_of_scope = [x for x in self._out_of_scope.split(';') if x]

            for dto in spider_head_dtos:
                if dto.key not in checked_keys and all(oos not in dto.url for oos in out_of_scope):
                    checked_keys.add(dto.key)
                    self._head_dtos.append(dto)

            filtered_urls = [dto.url for dto in self._head_dtos]

            self._thread_manager.run_all(self.__get_forms, filtered_urls, debug_msg='forms_searching')

            cache_manager.cache_result({head_key: self._head_dtos, form_key: self._form_dtos},
                                       cleanup_prev_results=True)

        return self._head_dtos, self._form_dtos

    def __get_forms(self, url: str):

        response = self._request_handler.handle_request(url, timeout=3)
        if response is None:
            return

        if any(dto.response_length == len(response.text) and
               dto.status_code == response.status_code and
               urlparse(dto.url).netloc == urlparse(url).netloc
               for dto in self._get_dtos):
            return

        get_dto = GetRequestDTO(url, response)
        self._get_dtos.append(get_dto)

        form_dto = self._request_checker.find_forms(url, response.text, get_dto, self._form_dtos)
        if form_dto and not all(form_dto.key != dto.key for dto in self._form_dtos):
            self._form_dtos.append(form_dto)

    def __check_urls(self, url: str):

        url_parts = urlparse(url)
        if url_parts.path in self._checked_hrefs or URL_IGNORE_EXT_REGEX.search(url):
            return
        else:
            self._checked_hrefs.add(url_parts.path)

        check = self._request_handler.send_head_request(url)
        if check is None:
            return

        response = self._request_handler.send_head_request(url, timeout=3)
        if response is None:
            return

        if response.status_code in VALID_STATUSES:
            self._head_dtos.append(HeadRequestDTO(response))
