import os
import re
import urllib.parse as urlparse
from typing import List
from collections import defaultdict
from Models.FormRequestDTO import FormRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class ManualTesting:
    def __init__(self, domain):
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self.__class__.__name__}'
        self._already_added_pathes = {}

    def save_urls_for_manual_testing(self, spider_dtos: List[HeadRequestDTO], form_dtos: List[FormRequestDTO]) \
            -> List[HeadRequestDTO]:

        groups = defaultdict(list)

        for obj in spider_dtos:
            groups[obj.url] = obj

        get_dtos = groups.values()

        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

        txt_filepath = f"{self._tool_result_dir}/{self._domain.replace(':','_')}_manual.txt"
        if os.path.exists(txt_filepath):
            return get_dtos

        get_result = set()
        checked_urls = set()
        for dto in get_dtos:

            is_added = self.__check_if_added(dto.url)
            if is_added:
                continue

            if re.search(r'\{(.*?)\}', dto.url):
                to_check = dto.url.rsplit('}', 1)[0]
                if to_check not in checked_urls:
                    checked_urls.add(to_check)
                    get_result.add(dto.url)
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

        if len(form_result) == 0 and len(get_result) == 0:
            return get_dtos

        txt_file = open(txt_filepath, 'a')
        for item in get_result:
            txt_file.write("%s\n" % str(item))

        if len(form_result) > 0:
            txt_file.write(f"\n{'-' * 100}\n")

            for item in form_result:
                txt_file.write("%s\n" % str(item))
        txt_file.close()

        return get_dtos

    def __check_if_added(self, url):
        is_already_added = False
        parsed = urlparse.urlparse(url)
        params_to_check = filter(None, parsed.query.split("&"))
        key_to_check = ''
        for param_to_check in params_to_check:
            param_value_split = param_to_check.split('=')
            key_to_check += f'{param_value_split[0]};'

        added_path = self._already_added_pathes.get(parsed.path)
        if added_path:
            if key_to_check in added_path:
                is_already_added = True
            else:
                self._already_added_pathes[parsed.path].append(key_to_check)
        else:
            self._already_added_pathes[parsed.path] = [key_to_check]

        return is_already_added
