import os
from typing import List

from Models.FormRequestDTO import FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO


class ManualTesting:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'

    def save_urls_for_manual_testing(self, spider_dtos: List[GetRequestDTO], form_dtos: List[FormRequestDTO]):
        get_dtos: List[GetRequestDTO] = []
        for dto in spider_dtos:
            if not any(dto.url == item.url for item in get_dtos):
                get_dtos.append(dto)

        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

        txt_filepath = f"{self._tool_result_dir}/{self._domain}_manual.txt"
        if os.path.exists(txt_filepath):
            return get_dtos

        get_result = set()
        checked_urls = set()
        for dto in get_dtos:
            if '?' in dto.url:
                to_check = dto.url.split('?')[0]
                if to_check not in checked_urls:
                    checked_urls.add(to_check)
                    get_result.add(dto.url)

        form_result = set()
        checked_urls = set()
        for dto in form_dtos:
            to_check = dto.url
            if to_check not in checked_urls:
                checked_urls.add(to_check)
                form_result.add(str(dto))

        txt_file = open(txt_filepath, 'a')
        for item in get_result:
            txt_file.write("%s\n" % str(item))

        txt_file.write(f"{'-' * 100}\n")

        for item in form_result:
            txt_file.write("%s\n" % str(item))
        txt_file.close()

        return get_dtos
