import os
import shutil

from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper


class Dnsx:
    def __init__(self, domain):
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheHelper(self._tool_name, domain)
        self._domain_folder = f'{os.environ.get("app_cache_result_path")}{self._tool_name}/{self._domain}'

    def get_ips(self, subdomains) -> set:

        ips = self._cache_manager.get_saved_result()
        if not ips and not isinstance(ips, set):

            if not os.path.exists(self._domain_folder):
                os.makedirs(self._domain_folder)

            subs_file = f'{self._domain_folder}/subs.txt'
            json_file = open(subs_file, 'w')
            for subdomain in subdomains:
                json_file.write(f"{subdomain}\n")
            json_file.close()

            cmd_arr = ['dnsx', '-l', subs_file, '-silent', '-a', '-resp-only']
            pk = ProcessHandler()
            bash_outputs = pk.run_temp_process(cmd_arr, self._domain, timeout=1200)

            ips = set()

            for output in bash_outputs:
                split = output.split('.')
                if len(split) == 4:
                    new_ips = set()
                    for i in range(1, 255):
                        new_ips.add(f'{split[0]}.{split[1]}.{split[2]}.{i}')
                    ips.update(new_ips)

            shutil.rmtree(self._domain_folder, ignore_errors=True)

            self._cache_manager.save_result(ips)

        return ips
