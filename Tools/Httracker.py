import os
import shutil
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper


class Httracker:
    def __init__(self, domain):
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheHelper(self._tool_name, domain)
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'

        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

    def check_single_url(self, url):

        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:

            domain_dir = f'{self._tool_result_dir}/{self._domain}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            cookie_manager = CookieHelper(self._domain)
            raw_cookies = cookie_manager.get_raw_file()
            cookies_arg = ''
            if raw_cookies:
                cookies_arg = f'--cookies={raw_cookies}'

            output_file = f'{self._tool_result_dir}/{self._domain}.txt'
            command = (f"cd {domain_dir}; httrack {url} --max-size=1000000 {cookies_arg} ; " +
                       "grep -e 'secret' -e 'passw' -e 'admin' -e 'apikey' -e 'api_key' -e 'accesskey' * -r " +
                       "--exclude=hts-log.txt --exclude-dir=hts-cache --exclude=*.css " +
                       "| awk '{print substr($0, 1, 1000)}' " +
                       f"> {output_file}")

            print(f'Cmd executing: {command}')
            stream = os.popen(command)
            stream.read()

            if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                os.remove(output_file)

            shutil.rmtree(domain_dir, ignore_errors=True)
