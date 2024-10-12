import os
from urllib.parse import urlparse

import inject

from Common.Logger import Logger


class S500Handler:
    def __init__(self):
        self._res_500_error_key_path = 'Results/500_error_keys.json'
        self._res_500_error_urls_path = 'Results/500_error_urls.txt'
        self._logger = inject.instance(Logger)

    def save_server_errors(self, errors):
        if len(errors) == 0:
            return 0

        checked_key_urls = {}
        for error in errors:
            url = error['url']
            netloc = urlparse(url).netloc
            key = f'{netloc};{error["response_len"]}'
            if key in checked_key_urls:
                continue
            else:
                checked_key_urls[key] = url

        if not os.path.exists(self._res_500_error_key_path):
            json_file = open(self._res_500_error_key_path, 'w')
            for key in checked_key_urls.keys():
                json_file.write(f"{key}\n")
            json_file.close()
            txt_file = open(self._res_500_error_urls_path, 'w')
            for url in checked_key_urls.values():
                txt_file.write(f"{url}\n")
            txt_file.close()
            new_errors_count = len(checked_key_urls)
        else:
            json_file = open(self._res_500_error_key_path, 'r', encoding='utf-8', errors='ignore')
            stored_keys = json_file.readlines()
            json_file.close()
            filtered_keys = list([k_v for k_v in checked_key_urls if f'{k_v}\n' not in stored_keys])
            if len(filtered_keys) > 0:
                json_file = open(self._res_500_error_key_path, 'a')
                txt_file = open(self._res_500_error_urls_path, 'a')
                for key in filtered_keys:
                    json_file.write(f"{key}\n")
                    txt_file.write(f"{checked_key_urls[key]}\n")
                json_file.close()
                txt_file.close()
            new_errors_count = len(filtered_keys)

        self._logger.log_warn(f'Added {new_errors_count} unique errors')
