import os
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from Common.ProcessKiller import ProcessKiller
from Managers.CacheManager import CacheManager
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.FormRequestDTO import FormDetailsDTO, FormRequestDTO
from Models.GetRequestDTO import GetRequestDTO


class Feroxbuster:
    def __init__(self, domain, cookies, headers, raw_cookies):
        self._headers = headers
        self._form_dtos: List[FormRequestDTO] = []
        self._get_dtos: List[GetRequestDTO] = []
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheManager(self._tool_name, domain)
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._request_handler = RequestHandler(cookies, headers)
        self._raw_cookies = raw_cookies
        self._had_found_too_many_urls = False

    def check_single_url(self, url,
                         already_exist__get_dtos: List[GetRequestDTO],
                         already_exist__form_dtos: List[FormRequestDTO]):

        dtos = self._cache_manager.get_saved_result()
        if not dtos and not isinstance(dtos, List):

            self._form_dtos = already_exist__form_dtos
            report_lines = self.__run_tool_cmd(url)

            ready_urls = self.__get_ready_urls(report_lines, already_exist__get_dtos)
            self._had_found_too_many_urls = len(ready_urls) > 1000
            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url, ready_urls, debug_msg=self._tool_name)
            already_exist__get_dtos.extend(self._get_dtos)
            self._cache_manager.save_result({'get_dtos': self._get_dtos, 'form_dtos': self._form_dtos})

        else:
            self._get_dtos = dtos['get_dtos']
            self._form_dtos = dtos['form_dtos']

        return self._get_dtos, self._form_dtos

    def __check_url(self, url):
        response = self._request_handler.handle_request(url)
        if response is None:
            return

        if not self._had_found_too_many_urls and any(dto for dto in self._get_dtos if
                                                     dto.status_code == response.status_code and
                                                     dto.response_length != len(response.text)):
            return

        if self._had_found_too_many_urls and \
                (str(response.status_code).startswith('2') or str(response.status_code).startswith('5')):
            return

        get_dto = GetRequestDTO(url, response)
        self._get_dtos.append(get_dto)
        form_dto = self.__find_forms(url, response.text, get_dto)
        if form_dto:
            self._form_dtos.append(form_dto)

    def __find_forms(self, target_url, web_page, dto: GetRequestDTO):
        if '<form' not in web_page:
            return
        forms = BeautifulSoup(web_page, "html.parser").findAll('form')
        if forms:
            form_details: List[FormDetailsDTO] = []
            for form in forms:
                action_tag = BeautifulSoup(str(form), "html.parser").find('form').get('action')
                parsed_parts = urlparse(target_url)
                if not action_tag:
                    action_tag = target_url
                elif action_tag.startswith('http'):
                    main_domain = '.'.join(parsed_parts.netloc.split('.')[-2:])
                    if main_domain not in action_tag:
                        continue
                    action_tag = action_tag
                elif action_tag.startswith('/'):
                    base_url = f'{parsed_parts.scheme}://{parsed_parts.netloc}'
                    action_tag = base_url + action_tag

                if any(form_dto for form_dto in self._form_dtos if
                       any(param for param in form_dto.form_params if param.action == action_tag)):
                    continue

                method = BeautifulSoup(str(form), "html.parser").find('form').get('method')
                method = method if method else "post"
                input_tags = BeautifulSoup(str(form), "html.parser").findAll('input')
                params = {}
                for input_tag in input_tags:
                    param_name = BeautifulSoup(str(input_tag), "html.parser").find('input').get('name')
                    if param_name:
                        default_value = BeautifulSoup(str(input_tag), "html.parser").find('input').get('value')
                        if default_value is None:
                            default_value = ''
                        params[param_name] = default_value
                form_details.append(FormDetailsDTO(action_tag.strip(), params, method))
            return FormRequestDTO(target_url, form_details, dto.status_code, dto.response_length)

    def __run_tool_cmd(self, url) -> [str]:

        output_file = f'{self._tool_result_dir}/RAW_{self._domain}.txt'
        cmd = ["feroxbuster", "--url", url, "--silent",
               "-w", f"{self._app_wordlists_path}directories.txt",
               "-o", output_file, "--insecure"]
        if len(self._raw_cookies) > 0:
            cmd.append("-b")
            cmd.append(self._raw_cookies)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({url}) Feroxbuster starts...')

        pk = ProcessKiller()
        pk.run_temp_process(cmd, url)
        report_lines = []

        if os.path.exists(output_file):
            main_txt_file = open(output_file, 'r')
            report_lines = main_txt_file.readlines()
            if os.path.getsize(output_file) == 0:
                os.remove(output_file)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({url}) Feroxbuster finished!')
        return report_lines

    def __get_ready_urls(self, report_lines: [], already_exist_dtos: List[GetRequestDTO]) -> set:
        filtered_output = set()
        for line in report_lines:
            if '=>' in line:
                redirected_url = line.split('=>', 1)[1]
                filtered_output.add(redirected_url.strip())
            else:
                filtered_output.add(line.strip())

        already_exist_urls = (dto.url for dto in already_exist_dtos)
        ready_urls = set()
        for url in filtered_output:
            if url not in already_exist_urls and url not in ready_urls:
                ready_urls.add(url)
        return ready_urls
