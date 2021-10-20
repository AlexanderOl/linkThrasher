import os
import threading

from Managers.MainFlowManager import MainFlowManager


class ThreadManager:
    def __init__(self, batch_size, download_path, max_depth, headers, ngrok_url):
        self.batch_size = batch_size
        self.download_path = download_path
        self.main_man = MainFlowManager(ngrok_url, max_depth, download_path, headers)

    def run_single(self, start_url: str):
        self.main_man.run_main_flow(start_url, True)

    def run_all(self):
        file_path = 'Targets\\urls.txt'
        if os.path.exists(file_path):
            urls = list(set(line.strip() for line in open(file_path)))
            url_batches = self.__chunks(urls)
            for batch in url_batches:
                threads = []
                for start_url in batch:
                    t = threading.Thread(target=self.main_man.run_main_flow, args=(start_url,False))
                    t.daemon = True
                    threads.append(t)

                for i in threads:
                    i.start()

                for i in threads:
                    i.join()
        else:
            print(f'{file_path} is missing')

    def __download_start_urls(self):
        file_path = f'{self.download_path}\\urls.txt'


    def __chunks(self, lst):
        n = max(1, self.batch_size)
        return (lst[i:i + n] for i in range(0, len(lst), n))
