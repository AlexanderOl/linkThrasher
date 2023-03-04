import subprocess
from threading import Timer
from typing import List
from urllib.parse import urlparse


def run_temp_process(cmd_arr, cache_key) -> List[str]:

    proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    kill_action = lambda process: process.kill()
    my_timer = Timer(1200, kill_action, [proc])
    try:
        my_timer.start()
        proc.wait()
        lines = proc.stderr.readlines()
        bash_output = []
        for line in lines:
            bash_output.append(line.decode().strip())

        print(f'({cache_key}); cmd - {" ".join(cmd_arr)}')
        return bash_output
    finally:
        my_timer.cancel()

