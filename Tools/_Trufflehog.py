import os
import subprocess
from datetime import datetime
from threading import Timer

from Helpers.CacheHelper import CacheHelper


class Trufflehog:
    def __init__(self, domain):
        self._domain = domain
        self._tool_name = self.__class__.__name__
        self._cache_manager = CacheHelper(self._tool_name, domain)
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._result_linkfinder_dir = f'{os.environ.get("app_result_path")}LinkFinder/{domain}'

    def check_secrets(self):
        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:

            output_file = f'{self._tool_result_dir}/RAW_{self._domain}.txt'
            proc = subprocess.Popen(["trufflehog", "filesystem", self._result_linkfinder_dir, "--only-verified",
                                     ">", output_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            then = datetime.now()
            kill_action = lambda process: process.kill()
            my_timer = Timer(600, kill_action, [proc])

            try:
                my_timer.start()
                proc.wait()
                proc.stderr.read()

                if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                    os.remove(output_file)

                duration = datetime.now() - then
                self._cache_manager.save_result([f'Trufflehog finished in {duration.total_seconds()} seconds'])

            finally:
                if my_timer.is_alive():
                    my_timer.cancel()
