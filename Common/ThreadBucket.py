import os
import threading
import random
import time
from copy import deepcopy

import inject

from Common.Logger import Logger


class ThreadBucket:
    def __init__(self):
        self.batch_size = int(os.environ.get('bucket_size'))
        self._logger = inject.instance(Logger)

    def run_all(self, action, items, debug_msg=False):
        to_process_items = deepcopy(items)
        random.shuffle(list(to_process_items))
        threads = []

        while len(to_process_items) > 0 or len(threads) > 0:
            self._logger.log_info(f'---===TM msg: {debug_msg}; counter: {round(len(to_process_items), 1)} left ===---')

            finished_threads = [thread for thread in threads if not thread.is_alive()]
            for thread in finished_threads:
                threads.remove(thread)

            items_to_pop_count = self.batch_size
            if len(to_process_items) < self.batch_size:
                items_to_pop_count = len(to_process_items)
            items_to_pop_count -= len(threads)
            if items_to_pop_count == 0:
                time.sleep(5)
                continue

            curr_items = [to_process_items.pop() for _ in range(items_to_pop_count)]
            for item in curr_items:
                t = threading.Thread(target=action, args=(item,))
                t.daemon = True
                threads.append(t)

            for i in threads:
                if not i.is_alive():
                    i.start()

            time.sleep(5)
