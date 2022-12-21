import os
import threading


class ThreadManager:
    def __init__(self):
        self.batch_size = int(os.environ.get('batch_size'))

    def run_all(self, action, items):
        url_batches = self.__chunks(items)
        count_left = len(url_batches)
        for batch in url_batches:
            print(f'ThreadManager counter: {count_left} left')
            threads = []
            for start_url in batch:
                t = threading.Thread(target=action, args=(start_url,))
                t.daemon = True
                threads.append(t)

            for i in threads:
                i.start()

            for i in threads:
                i.join()
            count_left -= 1

    def __chunks(self, items):
        lst = list(items)
        n = max(1, self.batch_size)
        return (lst[i:i + n] for i in range(0, len(lst), n))
