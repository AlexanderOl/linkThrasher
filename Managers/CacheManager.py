import os
import pickle
import shutil


class CacheManager:
    def __init__(self, file_name, domain):
        self.file_name = file_name
        self.domain = domain
        self.links_file = f"{self.file_name}/{self.domain}.json"

    @staticmethod
    def clear_all():
        path_list = ['SqliManagerGetResult', 'XssManagerGetResult', 'XssManagerFormResult', 'SsrfManagerResult', 'FormRequestFetcherResult']
        for path in path_list:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.mkdir(path)

    def get_saved_result(self):
        if os.path.exists(self.links_file):
            file = open(self.links_file, 'rb')
            data = pickle.load(file)
            file.close()
            return data

    def save_result(self, result):
        file = open(self.links_file, 'ab')
        pickle.dump(result, file)
        file.close()
