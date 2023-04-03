from datetime import datetime
import subprocess
import re
from threading import Timer
from typing import List


class ProcessKiller:
    def __init__(self):
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def run_temp_process(self, cmd_arr, cache_key, timeout=1200) -> List[str]:

        proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({cache_key}) Process started cmd - {" ".join(cmd_arr)}')

            outs, errs = proc.communicate(timeout=timeout)
            lines = outs.decode().strip().split('\n')

            if proc.returncode == 0:
                result = list([self._ansi_escape.sub('', line) for line in lines])
            else:
                result = [errs.decode()]

            print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({cache_key}) Process finished with code - {proc.returncode}')

            return result

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.terminate()
            return ['timeout']

        except Exception as inst:
            print(f'ProccessKillerException: {inst}')
