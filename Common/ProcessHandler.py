import os
from datetime import datetime
import subprocess
import re
from typing import List


class ProcessHandler:
    def __init__(self):
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def run_temp_process(self, cmd_arr, cache_key=None, timeout=1200) -> List[str]:

        proc = subprocess.Popen(cmd_arr, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:

            if cache_key:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({cache_key}) Process started cmd - {" ".join(cmd_arr)}')

            outs, errs = proc.communicate(timeout=timeout)
            lines = list(filter(None, outs.decode('utf-8').strip().split('\n')))

            if proc.returncode == 0:
                result = list([self._ansi_escape.sub('', line) for line in lines])
            else:
                result = [errs.decode()]

            if cache_key:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({cache_key}) Process finished with code - {proc.returncode}')

            return result

        except subprocess.TimeoutExpired as timeErr:
            proc.kill()
            proc.terminate()
            if timeErr.stdout:
                lines = timeErr.stdout.decode().strip().split('\n')
                result = list([self._ansi_escape.sub('', line) for line in lines])
                return result
            else:
                return ['timeout']

        except Exception as inst:
            print(f'ProcessHandler exception: {inst}')

        return []
