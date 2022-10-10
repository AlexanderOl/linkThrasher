import os
import pickle
from datetime import datetime


class CacheManager:
    def __init__(self, file_name, domain):
        self.result_dir = f"Results/{file_name}"
        self.result_filepath = f"{self.result_dir}/{domain}.json"
        self.read_result_filepath = f"{self.result_dir}/{domain}.txt"

    @staticmethod
    def clear_all():
        path_list = ['LinksManager',
                     'SqliManager',
                     'XssManager/Get',
                     'XssManager/Form',
                     'SstiManagerR/Get',
                     'SstiManager/Form',
                     'SsrfManager',
                     'FormRequestFetcher',
                     'Amass',
                     'Sublister']
        for path in path_list:
            result_path = f'Results/{path}'
            files = [f for f in os.listdir(result_path)]
            for f in files:
                os.remove(os.path.join(result_path, f))

    def get_saved_result(self):
        if os.path.exists(self.result_filepath):
            file = open(self.result_filepath, 'rb')
            data = pickle.load(file)
            file.close()
            return data

    def save_result(self, result, has_final_result=False):
        if len(result) > 0:

            if not os.path.exists(self.result_dir):
                os.makedirs(self.result_dir)

            json_file = open(self.result_filepath, 'ab')
            pickle.dump(result, json_file)
            json_file.close()

            txt_file = open(self.read_result_filepath, 'a')
            for item in result:
                # write each item on a new line
                txt_file.write("%s\n" % str(item))
            txt_file.close()

            if has_final_result:
                file = open('Results/Final.txt', 'a')
                res = f'[{datetime.now().strftime("%H:%M:%S")}]: {self.result_filepath} found {len(result)} \n'
                file.write(res)


