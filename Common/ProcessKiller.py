import subprocess
import re
from threading import Timer


class ProcessKiller:
    def __init__(self):
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def run_temp_process(self, cmd_arr, cache_key) -> str:

        proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        kill_action = lambda process: process.kill()
        my_timer = Timer(1200, kill_action, [proc])
        try:
            my_timer.start()
            proc.wait()
            msg = proc.stderr.read().decode()

            print(f'({cache_key}); msg - {msg}; code - {proc.returncode}; cmd - {" ".join(cmd_arr)}')

            return self._ansi_escape.sub('', msg)
        finally:
            my_timer.cancel()
