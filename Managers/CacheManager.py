import os
import pickle


class CacheManager:
    def __init__(self, fileName, domain):
        self.fileName = fileName
        self.domain = domain
        self.links_file = f"{self.fileName}/{self.domain}.json"

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


