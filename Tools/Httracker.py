import os
import shutil

from Helpers.CacheHelper import CacheHelper
from Helpers.CookieHelper import CookieHelper


class Httracker:
    def __init__(self, domain):
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheHelper(self._tool_name, domain)
        self._tool_domain_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}/{domain}'

        if not os.path.exists(self._tool_domain_result_dir):
            os.makedirs(self._tool_domain_result_dir)

    def check_single_url(self, url):

        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:

            site_dir = f'{self._tool_domain_result_dir}/site'
            if not os.path.exists(site_dir):
                os.makedirs(site_dir)

            cookie_manager = CookieHelper(self._domain)
            raw_cookies = cookie_manager.get_raw_file()
            cookies_arg = ''
            if raw_cookies:
                cookies_arg = f'--cookies={raw_cookies}'

            output_file = f'{self._tool_domain_result_dir}/RESULT_{self._domain}.txt'
            command = (f'cd {site_dir}; httrack {url} --max-size=1000000 {cookies_arg} ; '
                       "grep -e 'secret' -e 'passw' -e 'admin' -e 'apikey' -e 'api_key' -e 'accesskey' * -r "
                       "--exclude=hts-log.txt --exclude-dir=hts-cache " +
                       "| awk '{print substr($0, 1, 1000)}' "
                       f"> {output_file}")

            print(f'Cmd executing: {command}')
            stream = os.popen(command)
            stream.read()

            if os.path.getsize(output_file) == 0:
                shutil.rmtree(self._tool_domain_result_dir, ignore_errors=True)

            shutil.rmtree(site_dir, ignore_errors=True)
