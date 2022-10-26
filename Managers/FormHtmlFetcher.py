import json
from datetime import datetime

from bs4 import BeautifulSoup

from Managers.CacheManager import CacheManager
from Models.FormRequestDTO import FormRequestDTO
from Models.FormRequestDTO import FormDetailsDTO
from Models.GetRequestDTO import GetRequestDTO
from typing import List


def parse_forms(link, forms):
    result: List[FormDetailsDTO] = []
    for form in forms:
        action_tag = BeautifulSoup(str(form), "html.parser").find('form').get('action')
        if not action_tag:
            action_tag = link
        elif action_tag.startswith('http'):
            action_tag = action_tag
        elif action_tag.startswith('/'):
            action_tag = link + action_tag

        method = BeautifulSoup(str(form), "html.parser").find('form').get('method')
        method = method if method else "post"
        input_tags = BeautifulSoup(str(form), "html.parser").findAll('input')
        params = {}
        for input_tag in input_tags:
            param_name = BeautifulSoup(str(input_tag), "html.parser").find('input').get('name')
            if param_name:
                default_value = BeautifulSoup(str(input_tag), "html.parser").find('input').get('value')
                params[param_name] = default_value
        result.append(FormDetailsDTO(action_tag, params, method))
    return result


def get_post_data(dto: GetRequestDTO) -> FormRequestDTO:
    forms = BeautifulSoup(dto.web_page, "html.parser").findAll('form')
    if forms:
        form_dtos = parse_forms(dto.link, forms)
        return FormRequestDTO(dto.link, form_dtos)


class FormRequestFetcher:
    def __init__(self, domain):
        self.domain = domain

    def get_all_post_requests(self, get_DTOs: List[GetRequestDTO]) -> List[FormRequestDTO]:

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: FormRequestFetcher started...')

        cache_manager = CacheManager('FormRequestFetcher', self.domain)
        result = cache_manager.get_saved_result()
        if not result:
            result: List[FormRequestDTO] = []
            for dto in get_DTOs:
                found = get_post_data(dto)
                if found:
                    result.append(found)
            cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: FormRequestFetcher found {len(result)} items')
        return result
