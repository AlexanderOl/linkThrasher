import os
import pathlib
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from Common.CollectionUtil import CollectionUtil
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Models.HeadRequestDTO import HeadRequestDTO


class EyeWitness:
    def __init__(self, cache_key, headers):
        self._tool_name = self.__class__.__name__
        self._cache_key = cache_key
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._chunk_size = 30
        self._tool_dir = f"Results/{self._tool_name}"
        self._request_handler = RequestHandler('', headers)

    def visit_dtos(self, dtos: List[HeadRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._cache_key}) Eyewitness will visit {len(dtos)} urls')

        if len(dtos) == 0:
            return
        cache_manager = CacheHelper(self._tool_name, self._cache_key)
        result = cache_manager.get_saved_result()
        if not result:

            if not os.path.exists(self._tool_dir):
                os.makedirs(self._tool_dir)

            domain_dir = f'{self._tool_dir}/{self._cache_key}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            start = datetime.now()
            batches = CollectionUtil.divide_chunks(dtos, self._chunk_size)
            counter = len(batches)
            for urls_batch in batches:
                msg = self.__make_screens(urls_batch, counter)
                counter -= 1
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(urls_batch)}, result:{msg}')

            self.__cleanup()

            urls = [f.url for f in dtos]
            duration = datetime.now() - start
            result = f'({self._cache_key}) Eyewitness finished in {duration.total_seconds()} seconds'
            cache_manager.cache_result(urls)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: {result}')

    def __make_screens(self, dtos_batch: List[HeadRequestDTO], counter: int):

        counter_directory_path = f'{self._tool_result_dir}/{self._cache_key}/{counter}'
        if os.path.exists(counter_directory_path):
            return f"{counter_directory_path} exits"

        txt_filepath = f"{self._tool_dir}/{self._cache_key}_temp.txt"
        txt_file = open(txt_filepath, 'w')
        for dto in dtos_batch:
            txt_file.write("%s\n" % str(dto.url))
        txt_file.close()
        result_msg = '<empty>'
        try:
            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)

            cmd_arr = ['eyewitness', '-f', subdomains_filepath, '--thread', '3', '--web',
                       '-d', counter_directory_path, '--timeout', '15', '--no-prompt']

            pk = ProcessHandler()
            lines = pk.run_temp_process(cmd_arr, self._cache_key)
            for line in lines:
                if 'Finished in' in line:
                    result_msg = line.replace('\n', '')

        except Exception as inst:
            result_msg = f'EyeWitness Exception ({inst}) Cache Key:({self._cache_key})'
            print(result_msg)

        os.remove(txt_filepath)

        return result_msg

    def __cleanup(self):
        copy_all_cmd = f"cd {self._tool_result_dir}/{self._cache_key}; " + \
                       "mkdir all -p && find . -name '*.png' -exec cp {} " + \
                       f'{self._tool_result_dir}/{self._cache_key}/all/ \; 2>>/dev/null'
        stream = os.popen(copy_all_cmd)
        stream.read()

        clean_up_cmd = f"cd {self._tool_result_dir}/{self._cache_key}; " + \
                       "find . ! -name 'all' -type d -exec rm -r {} + 2>>/dev/null"
        stream = os.popen(clean_up_cmd)
        stream.read()

    def visit_errors(self, errors):
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

        self.__visit_urls(checked_urls)

    def __visit_urls(self, urls: set):
        dtos: List[HeadRequestDTO] = []
        for url in urls:
            response = self._request_handler.send_head_request(url)
            if response is not None:
                dtos.append(HeadRequestDTO(response))
        self.visit_dtos(dtos)
