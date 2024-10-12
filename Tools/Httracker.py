import os
import shutil
from urllib.parse import urlparse

import inject

from Common.Logger import Logger
from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper


class Httracker:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._app_wordlists_path = f'{os.environ.get("app_wordlists_path")}'
        self._logger = inject.instance(Logger)
        self._cookie_manager = inject.instance(CookieHelper)
        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

    def check_single_url(self, url):
        domain = urlparse(url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        report_lines = cache_manager.get_saved_result()
        if not report_lines:

            domain_dir = f'{self._tool_result_dir}/{domain}'
            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            raw_cookies = self._cookie_manager.get_raw_file(domain)
            cookies_arg = ''
            if raw_cookies:
                cookies_arg = f'--cookies={raw_cookies}'

            output_file = f'{self._tool_result_dir}/{domain}.txt'
            command = (f"cd {domain_dir}; httrack {url} --max-size=1000000 {cookies_arg} ; " +
                       f"grep -f {self._app_wordlists_path}secret-keywords.txt " +
                       "* -r --exclude=hts-log.txt --exclude-dir=hts-cache --exclude=*.css " +
                       "| awk '{print substr($0, 1, 1000)}' " +
                       f"> {output_file}")

            self._logger.log_info(f'Cmd executing: {command}')
            stream = os.popen(command)
            stream.read()

            if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                os.remove(output_file)

            shutil.rmtree(domain_dir, ignore_errors=True)

            cache_manager.cache_result([f'{self._tool_name} finished'])
