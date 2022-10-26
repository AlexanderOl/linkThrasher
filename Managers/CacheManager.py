import os
import pickle
from datetime import datetime


class CacheManager:
    def __init__(self, tool_name, domain):
        self.result_dir = f"Results/{tool_name}"
        self.result_filepath = f"{self.result_dir}/{domain}.json"
        self.txt_result_filepath = f"{self.result_dir}/{domain}.txt"

    @staticmethod
    def clear_all():
        path_list = ['Amass',
                     'Dirb',
                     'FormRequestFetcher',
                     'LinksManager',
                     'Nmap',
                     'SqliManager',
                     'SstiManager/Get',
                     'SstiManager/Form',
                     'SsrfManager',
                     'Sublister',
                     'XssManager/Get',
                     'XssManager/Form']
        for path in path_list:
            result_path = f'Results/{path}'
            if os.path.exists(result_path):
                files = [f for f in os.listdir(result_path)]
                for f in files:
                    os.remove(os.path.join(result_path, f))

    def get_saved_result(self):
        if os.path.exists(self.result_filepath):
            print(f"{self.result_filepath} already exists")
            file = open(self.result_filepath, 'rb')
            data = pickle.load(file)
            file.close()
            return data
        else:
            print(f"{self.result_filepath} not found")


    def save_result(self, result, has_final_result=False):
        if len(result) > 0:

            if not os.path.exists(self.result_dir):
                os.makedirs(self.result_dir)

            json_file = open(self.result_filepath, 'ab')
            pickle.dump(result, json_file)
            json_file.close()

            txt_file = open(self.txt_result_filepath, 'a')
            for item in result:
                txt_file.write("%s\n" % str(item))
            txt_file.close()

            if has_final_result:
                file = open('Results/Final.txt', 'a')
                res = f'[{datetime.now().strftime("%H:%M:%S")}]: {self.result_filepath} found {len(result)} \n'
                file.write(res)


