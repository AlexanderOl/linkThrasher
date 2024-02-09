import os
import pickle
import shutil
from datetime import datetime
from typing import List

from Models.HeadRequestDTO import HeadRequestDTO


class CacheHelper:
    def __init__(self, tool_name, domain: str):
        self._tool_result_dir = f"Results/{tool_name}"
        self._tracker_dir = "Tracker"
        self._tracker_filepath = f"{self._tracker_dir}/{domain.replace(':', '_')}.json"
        self._txt_tracker_filepath = f"{self._tracker_dir}/{domain.replace(':', '_')}.txt"
        self._result_filepath = f"{self._tool_result_dir}/{domain.replace(':', '_')}.json"
        self._txt_result_filepath = f"{self._tool_result_dir}/{domain.replace(':', '_')}.txt"
        self._domain = domain

    def get_saved_result(self):
        try:
            if not os.path.exists(self._tool_result_dir):
                os.makedirs(self._tool_result_dir)
            if os.path.exists(self._result_filepath) and os.path.getsize(self._result_filepath) > 0:
                file = open(self._result_filepath, 'rb')
                data = pickle.load(file)
                file.close()
                return data
        except:
            if os.path.exists(self._result_filepath):
                os.remove(self._result_filepath)

    def save_result(self, result, has_final_result=False, cleanup_prev_results=False):
        if cleanup_prev_results:
            shutil.rmtree(self._tool_result_dir, ignore_errors=True)

        if not os.path.exists(self._tool_result_dir):
            os.makedirs(self._tool_result_dir)

        json_file = open(self._result_filepath, 'wb')
        pickle.dump(result, json_file)
        json_file.close()

        if len(result) > 0:
            txt_file = open(self._txt_result_filepath, 'a')
            for item in result:
                txt_file.write("%s\n" % str(item))
            txt_file.close()

            if has_final_result:
                file = open('Results/Final.txt', 'a')
                res = f'[{datetime.now().strftime("%H:%M:%S")}]: {self._result_filepath} found {len(result)} \n'
                file.write(res)

    def get_tracked_subdomains(self) -> List[HeadRequestDTO]:
        try:
            if not os.path.exists(self._tracker_dir):
                os.makedirs(self._tracker_dir)
            if os.path.exists(self._tracker_filepath) and os.path.getsize(self._tracker_filepath) > 0:
                file = open(self._tracker_filepath, 'rb')
                data = pickle.load(file)
                file.close()
                return data
        except:
            if os.path.exists(self._tracker_filepath):
                os.remove(self._tracker_filepath)
        return []

    def save_tracker_result(self, result: List[HeadRequestDTO]):
        if not os.path.exists(self._tracker_dir):
            os.makedirs(self._tracker_dir)

        json_file = open(self._tracker_filepath, 'wb')
        pickle.dump(result, json_file)
        json_file.close()

        if len(result) > 0:
            txt_file = open(self._txt_tracker_filepath, 'a')
            for item in result:
                txt_file.write("%s\n" % str(item))
            txt_file.close()
