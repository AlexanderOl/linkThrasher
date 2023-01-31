import os
import pathlib
import re
from datetime import datetime
from Managers.CacheManager import CacheManager


class EyeWitness:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._chunk_size = 30
        self._tool_dir = f"Results/{self._tool_name}"
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def visit_urls(self, urls: set):
        if len(urls) == 0:
            return
        cache_manager = CacheManager(self._tool_name, self._domain)
        result = cache_manager.get_saved_result()
        if not result:

            if not os.path.exists(self._tool_dir):
                os.makedirs(self._tool_dir)

            domain_dir = f'{self._tool_dir}/{self._domain}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            start = datetime.now()
            batches_list = list(self.__divide_chunks(urls))
            counter = len(batches_list)
            for urls_batch in batches_list:
                msg = self.__make_screens(urls_batch, counter)
                counter -= 1
                print(
                    f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(urls_batch)}, result:{msg}')

            self.__cleanup()

            duration = datetime.now() - start
            result = f'Eyewitness ({self._domain})  finished in {duration.total_seconds()} seconds'
            cache_manager.save_result([result])

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: {result}')

    def __divide_chunks(self, items):
        items_to_split = list(items)
        for i in range(0, len(items_to_split), self._chunk_size):
            yield items_to_split[i:i + self._chunk_size]

    def __make_screens(self, urls_batch, counter: int):

        counter_directory_path = f'{self._tool_result_dir}/{self._domain}/{counter}'
        if os.path.exists(counter_directory_path):
            print(f"{counter_directory_path} exits")
            return
        txt_filepath = f"{self._tool_dir}/{self._domain}_raw.txt"
        txt_file = open(txt_filepath, 'w')
        for subdomain in urls_batch:
            txt_file.write("%s\n" % str(subdomain))
        txt_file.close()

        try:
            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
            command = f'cd /root/Desktop/TOOLs/EyeWitness/Python/; ' \
                      f'./EyeWitness.py -f {subdomains_filepath} --thread 1 --web -d {counter_directory_path} --timeout 15 --no-prompt'
            stream = os.popen(command)
            bash_outputs = stream.readlines()

            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                if 'Finished in' in encoded_line:
                    result_msg = encoded_line.replace('\n', '')
                    break
        except Exception as inst:
            result_msg = f'EyeWitness Exception ({inst}) Urls:({" ".join(urls_batch)})'
            print(result_msg)

        os.remove(txt_filepath)

        return result_msg

    def __cleanup(self):
        copy_all_cmd = f"cd {self._tool_result_dir}/{self._domain}; " + \
                       "mkdir all -p && find . -name '*.png' -exec cp {} " + \
                       f'{self._tool_result_dir}/{self._domain}/all/ \; 2>>/dev/null'
        stream = os.popen(copy_all_cmd)
        stream.read()

        clean_up_cmd = f"cd {self._tool_result_dir}/{self._domain}; " + \
                       "find . ! -name 'all' -type d -exec rm -r {} + 2>>/dev/null"
        stream = os.popen(clean_up_cmd)
        stream.read()
