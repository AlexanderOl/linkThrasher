import os
import pathlib
import re
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from Common import ProcessKiller
from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO


class EyeWitness:
    def __init__(self, cache_key, headers):
        self._tool_name = self.__class__.__name__
        self._cache_key = cache_key
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._chunk_size = 30
        self._tool_dir = f"Results/{self._tool_name}"
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self._request_handler = RequestHandler('', headers)

    def visit_urls(self, urls: set):
        dtos: List[GetRequestDTO] = []
        for url in urls:
            response = self._request_handler.handle_request(url)
            if response is not None:
                dtos.append(GetRequestDTO(url, response))
        self.visit_dtos(dtos)

    def visit_dtos(self, dtos: List[GetRequestDTO]):
        print(f'[{datetime.now().strftime("%H:%M:%S")}]:({self._cache_key}) Eyewitness will visit {len(dtos)} urls')

        if len(dtos) == 0:
            return
        cache_manager = CacheManager(self._tool_name, self._cache_key)
        result = cache_manager.get_saved_result()
        if not result:

            if not os.path.exists(self._tool_dir):
                os.makedirs(self._tool_dir)

            domain_dir = f'{self._tool_dir}/{self._cache_key}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            start = datetime.now()
            batches_list = list(self.__divide_chunks(dtos))
            counter = len(batches_list)
            for urls_batch in batches_list:
                msg = self.__make_screens(urls_batch, counter)
                counter -= 1
                print(
                    f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(urls_batch)}, result:{msg}')

            self.__cleanup()

            output_file = f'{self._tool_result_dir}/RAW_{self._cache_key}.txt'
            urls = [f.url for f in dtos]

            txt_file = open(output_file, 'w')
            for line in urls:
                    txt_file.write(f"{line}\n")
            txt_file.close()

            duration = datetime.now() - start
            result = f'Eyewitness ({self._cache_key})  finished in {duration.total_seconds()} seconds'
            cache_manager.save_result([result])

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: {result}')

    def __divide_chunks(self, items):
        items_to_split = list(items)
        for i in range(0, len(items_to_split), self._chunk_size):
            yield items_to_split[i:i + self._chunk_size]

    def __make_screens(self, dtos_batch: List[GetRequestDTO], counter: int):

        counter_directory_path = f'{self._tool_result_dir}/{self._cache_key}/{counter}'
        if os.path.exists(counter_directory_path):
            return f"{counter_directory_path} exits"

        txt_filepath = f"{self._tool_dir}/{self._cache_key}_temp.txt"
        txt_file = open(txt_filepath, 'w')
        for dto in dtos_batch:
            txt_file.write("%s\n" % str(dto.url))
        txt_file.close()
        result_msg = ''
        try:
            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)

            cmd_arr = ['python', '/root/Desktop/TOOLs/EyeWitness/Python/EyeWitness.py',
                       '-f', subdomains_filepath, '--thread','1', '--web',
                       '-d', counter_directory_path, '--timeout', '15', '--no-prompt']

            bash_outputs = ProcessKiller.run_temp_process(cmd_arr, self._cache_key)

            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                if 'Finished in' in encoded_line:
                    result_msg = encoded_line.replace('\n', '')
                    break

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

        self.visit_urls(checked_urls)
