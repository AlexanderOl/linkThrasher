import os
import pathlib
from datetime import datetime
from typing import List
from urllib.parse import urlparse

import inject

from Common.CollectionUtil import CollectionUtil
from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Models.HeadRequestDTO import HeadRequestDTO


class EyeWitness:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._chunk_size = 30
        self._tool_dir = f"Results/{self._tool_name}"
        self._process_handler = inject.instance(ProcessHandler)
        self._request_handler = inject.instance(RequestHandler)
        self._logger = inject.instance(Logger)

    def visit_dtos(self, domain: str, dtos: List[HeadRequestDTO]):
        self._logger.log_info(f'({domain}) Eyewitness will visit {len(dtos)} urls')

        if len(dtos) == 0:
            return
        cache_manager = CacheHelper(self._tool_name, domain)
        result = cache_manager.get_saved_result()
        if not result:

            if not os.path.exists(self._tool_dir):
                os.makedirs(self._tool_dir)

            domain_dir = f'{self._tool_dir}/{domain}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            start = datetime.now()
            batches = CollectionUtil.divide_chunks(dtos, self._chunk_size)
            counter = len(batches)
            for urls_batch in batches:
                msg = self.__make_screens(domain, urls_batch, counter)
                counter -= 1
                self._logger.log_info(f'left:{counter}, chunk_size:{len(urls_batch)}, result:{msg}')

            self.__cleanup(domain)

            urls = [f.url for f in dtos]
            duration = datetime.now() - start
            result = f'({domain}) Eyewitness finished in {duration.total_seconds()} seconds'
            cache_manager.cache_result(urls)

        self._logger.log_info(result)

    def __make_screens(self, domain: str, dtos_batch: List[HeadRequestDTO], counter: int):

        counter_directory_path = f'{self._tool_result_dir}/{domain}/{counter}'
        if os.path.exists(counter_directory_path):
            return f"{counter_directory_path} exists"

        txt_filepath = f"{self._tool_dir}/{domain}_temp.txt"
        txt_file = open(txt_filepath, 'w')
        for dto in dtos_batch:
            txt_file.write("%s\n" % str(dto.url))
        txt_file.close()
        result_msg = '<empty>'
        try:
            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)

            cmd_arr = ['eyewitness', '-f', subdomains_filepath, '--thread', '3', '--web',
                       '-d', counter_directory_path, '--timeout', '15', '--no-prompt']

            lines = self._process_handler.run_temp_process(cmd_arr, domain)
            for line in lines:
                if 'Finished in' in line:
                    result_msg = line.replace('\n', '')

        except Exception as inst:
            self._logger.log_error(f'EyeWitness Exception ({inst}) Cache Key:({domain})')

        os.remove(txt_filepath)

        return result_msg

    def __cleanup(self, domain: str):
        copy_all_cmd = f"cd {self._tool_result_dir}/{domain}; " + \
                       "mkdir all -p && find . -name '*.png' -exec cp {} " + \
                       f'{self._tool_result_dir}/{domain}/all/ \; 2>>/dev/null'
        stream = os.popen(copy_all_cmd)
        stream.read()

        clean_up_cmd = f"cd {self._tool_result_dir}/{domain}; " + \
                       "find . ! -name 'all' -type d -exec rm -r {} + 2>>/dev/null"
        stream = os.popen(clean_up_cmd)
        stream.read()

    def visit_errors(self, domain: str, errors):
        keys_to_check = set()
        checked_urls = set()
        for error in errors:
            url = error['url']
            netloc = urlparse(url).netloc
            response_length = len(error['response'].text)
            key = f'{netloc};{response_length}'
            if key in keys_to_check:
                continue
            else:
                keys_to_check.add(key)
            checked_urls.add(url)

        self.__visit_urls(domain, checked_urls)

    def __visit_urls(self, domain: str, urls: set):
        dtos: List[HeadRequestDTO] = []
        for url in urls:
            response = self._request_handler.send_head_request(url)
            if response is not None:
                dtos.append(HeadRequestDTO(response))
        self.visit_dtos(domain, dtos)
