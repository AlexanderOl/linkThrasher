import os
import pickle
from datetime import datetime


class CacheManager:
    def __init__(self, file_name, domain):
        self.links_file = f"Results/{file_name}/{domain}.json"

    @staticmethod
    def clear_all():
        path_list = ['LinksManagerResult',
                     'SqliManagerResult',
                     'XssManagerResult/Get',
                     'XssManagerResult/Form',
                     'SstiManagerResult/Get',
                     'SstiManagerResult/Form',
                     'SsrfManagerResult',
                     'FormRequestFetcherResult']
        for path in path_list:
            result_path = f'Results/{path}'
            files = [f for f in os.listdir(result_path)]
            for f in files:
                os.remove(os.path.join(result_path, f))

    def get_saved_result(self):
        if os.path.exists(self.links_file):
            file = open(self.links_file, 'rb')
            data = pickle.load(file)
            file.close()
            return data

    def save_result(self, result, has_final_result=False):
        file = open(self.links_file, 'ab')
        pickle.dump(result, file)
        file.close()

        if has_final_result and len(result) > 0:
            file = open('Results/Final.txt', 'a')
            res = f'[{datetime.now().strftime("%H:%M:%S")}]: {self.links_file} found {len(result)} \n'
            file.write(res)
