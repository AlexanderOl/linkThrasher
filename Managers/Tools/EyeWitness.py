import os
import pathlib
from datetime import datetime

from Managers.CacheManager import CacheManager


class EyeWitness:
    def __init__(self, domain):
        self.__tool_name = self.__class__.__name__
        self.__domain = domain
        self.__tool_result_dir = f'{os.environ.get("app_result_path")}{self.__tool_name}'

    def visit_urls(self, urls: set):
        if len(urls) == 0:
            return
        cache_manager = CacheManager(self.__tool_name, self.__domain)
        checked_domain = cache_manager.get_saved_result()
        if not checked_domain:

            tool_dir = f"Results/{self.__tool_name}"
            if not os.path.exists(tool_dir):
                os.makedirs(tool_dir)

            domain_dir = f'{tool_dir}/{self.__domain}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            txt_filepath = f"{tool_dir}/{self.__domain}_raw.txt"
            txt_file = open(txt_filepath, 'w')
            for subdomain in urls:
                txt_file.write("%s\n" % str(subdomain))
            txt_file.close()

            subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
            command = f'cd /root/Desktop/TOOLs/EyeWitness/Python/; ' \
                      f'./EyeWitness.py -f {subdomains_filepath} --web -d {self.__tool_result_dir}/{self.__domain} --timeout 15 --no-prompt'
            stream = os.popen(command)
            bash_outputs = stream.readlines()

            for line in bash_outputs:
                if 'Finished in' in line:
                    checked_domain = line.replace('\n', '')
                    break

            os.remove(txt_filepath)

            if checked_domain:
                cache_manager.save_result([checked_domain])
            else:
                print('EyeWitness was not finished properly')
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self.__domain}) {self.__tool_name} found {checked_domain} items')
