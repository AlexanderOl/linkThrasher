import os
import subprocess
from datetime import datetime
from threading import Timer

from Managers.CacheManager import CacheManager
from Managers.Tools.Dirb import Dirb


class Gobuster:
    def __init__(self, domain):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._cache_manager = CacheManager(self._tool_name, domain)

    def check_single_url(self, url):
        report_lines = self._cache_manager.get_saved_result()
        if not report_lines:
            try:
                then = datetime.now()
                print(f'[{then.strftime("%H:%M:%S")}]: Gobuster {url} start...')

                output_file = f'{self._tool_result_dir}/RAW_{self._domain}.txt'

                proc = subprocess.Popen(["gobuster", "dir", "-u", url, "-w" "/usr/share/dirb/wordlists/big.txt",
                                         "--no-error", "-t", "50", "--delay", "2000ms", "-o", output_file],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                kill = lambda process: process.kill()
                my_timer = Timer(1200, kill, [proc])
                try:
                    my_timer.start()
                    proc.wait()
                    err_message = proc.stderr.read().decode()

                    if 'Error: ' in err_message:
                        dirb = Dirb(self._domain)
                        dirb.check_single_url(url)
                    else:
                        print(f'({url}) err_message - {err_message}')

                finally:
                    my_timer.cancel()

                if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                    os.remove(output_file)

                print(f'[{datetime.now().strftime("%H:%M:%S")}]: Gobuster {url} finished.')
                duration = datetime.now() - then
                self._cache_manager.save_result([f'Gobuster finished in {duration.total_seconds()} seconds'])
            except Exception as inst:
                self._cache_manager.save_result([f'Gobuster finished with ERRORS in ({inst})'])
