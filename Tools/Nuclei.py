import os
import re
import subprocess
from datetime import datetime
from threading import Timer

from Managers.CacheManager import CacheManager
from Tools.Dirb import Dirb


class Nuclei:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._cache_manager = CacheManager(self._tool_name, domain)
        self._expected = ['[medium]', '[high]', '[critical]', '[unknown]', '[network]']
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def check_single_url(self, url):
        report_lines = self._cache_manager.get_saved_result()
        if not report_lines and not isinstance(report_lines, set):
            command = f"nuclei -u {url} " \
                      f"--exclude-matchers http-missing-security-headers,old-copyright,favicon-detect,ssl-issuer," \
                      f"tls-version,waf-detect,cname-fingerprint,akamai-cache-detect"
            stream = os.popen(command)
            bash_outputs = stream.readlines()

            result = set()
            for line in bash_outputs:
                encoded_line = self._ansi_escape.sub('', line)
                for keyword in self._expected:
                    if keyword in encoded_line:
                        result.add(encoded_line)
                print(line)

            self._cache_manager.save_result(result)

