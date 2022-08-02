import os
import threading

from Managers.SingleUrlFlowManager import SingleUrlFlowManager


class ThreadManager:
    def __init__(self, batch_size, download_path, max_depth, headers, ngrok_url):
        self.batch_size = int(batch_size)
        self.single_man = SingleUrlFlowManager(ngrok_url, max_depth, download_path, headers)

    def run_single(self, start_url: str, raw_cookies: str):
        self.single_man.run_main_flow(start_url, raw_cookies)

    def run_target_urls(self):
        file_path = 'Targets\\urls.txt'
        if os.path.exists(file_path):
            urls = list(set(line.strip() for line in open(file_path)))
            url_batches = self.__chunks(urls)
            for batch in url_batches:
                threads = []
                for start_url in batch:
                    t = threading.Thread(target=self.single_man.run_main_flow, args=(start_url,))
                    t.daemon = True
                    threads.append(t)

                for i in threads:
                    i.start()

                for i in threads:
                    i.join()
        else:
            print(os.path.dirname(os.path.realpath(__file__)))
            print(f'{file_path} is missing')

    def run_all(self, items, action):
        url_batches = self.__chunks(items)
        for batch in url_batches:
            threads = []
            for start_url in batch:
                t = threading.Thread(target=action, args=(start_url,))
                t.daemon = True
                threads.append(t)

            for i in threads:
                i.start()

            for i in threads:
                i.join()

    def __chunks(self, items):
        lst = list(items)
        n = max(1, self.batch_size)
        return (lst[i:i + n] for i in range(0, len(lst), n))
