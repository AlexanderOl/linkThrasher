import os
import pathlib
from datetime import datetime
from Managers.CacheManager import CacheManager


class EyeWitness:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._chunk_size = 30
        self._tool_dir = f"Results/{self._tool_name}"

    def divide_chunks(self, items):
        items_to_split = list(items)
        for i in range(0, len(items_to_split), self._chunk_size):
            yield items_to_split[i:i + self._chunk_size]

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
            batches_list = list(self.divide_chunks(urls))
            counter = len(batches_list)
            for urls_batch in batches_list:
                msg = self._visit_urls(urls_batch)
                counter -= 1
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: left:{counter}, chunk_size:{len(urls_batch)}, result:{msg}')

            duration = datetime.now() - start
            result = f'Eyewitness ({self._domain})  finished in {duration.total_seconds()} seconds'
            cache_manager.save_result([result])

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: {result}')

    def _visit_urls(self, urls_batch):
        txt_filepath = f"{self._tool_dir}/{self._domain}_raw.txt"
        txt_file = open(txt_filepath, 'w')
        for subdomain in urls_batch:
            txt_file.write("%s\n" % str(subdomain))
        txt_file.close()

        try:
            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
            command = f'cd /root/Desktop/TOOLs/EyeWitness/Python/; ' \
                      f'./EyeWitness.py -f {subdomains_filepath} --web -d {self._tool_result_dir}/{self._domain} --timeout 15 --no-prompt'
            stream = os.popen(command)
            bash_outputs = stream.readlines()

            for line in bash_outputs:
                if 'Finished in' in line:
                    result_msg = line.replace('\n', '')
                    break
        except Exception as inst:
            result_msg = f'EyeWitness Exception ({inst}) Urls:({" ".join(urls_batch)})'
            print(result_msg)

        os.remove(txt_filepath)

        return result_msg


