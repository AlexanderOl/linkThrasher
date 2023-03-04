import subprocess
from threading import Timer
from urllib.parse import urlparse


def run_temp_process(cmd_arr, cache_key):

    proc = subprocess.Popen(cmd_arr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    kill_action = lambda process: process.kill()
    my_timer = Timer(1200, kill_action, [proc])
    try:
        my_timer.start()
        proc.wait()
        msg = proc.stderr.read().decode()

        print(f'({cache_key}); msg - {msg}; cmd - {" ".join(cmd_arr)}')
        return msg
    finally:
        my_timer.cancel()

