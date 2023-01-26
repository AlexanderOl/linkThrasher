import os
import pathlib
import urllib.parse as urlparse
from datetime import datetime
from typing import List

from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO


class Lfimap:
    def __init__(self, domain):
        tool_name = self.__class__.__name__
        self._domain = domain
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{tool_name}'
        self._cache_manager = CacheManager(tool_name, domain)
        self._target_url_params = ['cat',
                                   'dir',
                                   'doc',
                                   'docs',
                                   'document',
                                   'action',
                                   'board',
                                   'date',
                                   'detail',
                                   'file',
                                   'download',
                                   'path',
                                   'folder',
                                   'prefix',
                                   'include',
                                   'page',
                                   'inc',
                                   'src',
                                   'img',
                                   'image',
                                   'locate',
                                   'publish',
                                   'attached',
                                   'attach',
                                   'json',
                                   'show',
                                   'xml',
                                   'db',
                                   'script',
                                   'js',
                                   'site',
                                   'config',
                                   'type',
                                   'view',
                                   'title',
                                   'locale',
                                   'local',
                                   'message',
                                   'msg',
                                   'source',
                                   'upload',
                                   'url',
                                   'content',
                                   'document',
                                   'layout',
                                   'mod',
                                   'conf',
                                   'output',
                                   'dbprefix',
                                   'exclude',
                                   'prev',
                                   'next',
                                   'pic',
                                   'pics',
                                   'pictures',
                                   'filename',
                                   'license',
                                   'pdf',
                                   'frontpage',
                                   'filepath',
                                   'view',
                                   'vid',
                                   'video',
                                   'dirs',
                                   'directory',
                                   'dictionary',
                                   'dict',
                                   'use',
                                   'imgpath',
                                   'txt',
                                   'article'
                                   ]
        self._already_added_pathes = {}

    def check_dtos(self, get_dtos: List[GetRequestDTO], start_url: str):

        result = self._cache_manager.get_saved_result()
        if not result and not isinstance(result, set):
            pwn_payloads = self.__create_pwn_payloads(get_dtos, start_url)
            payloads_filepath = self.__create_payloads_file(pwn_payloads)

            filepath = os.path.join(pathlib.Path().resolve(), payloads_filepath)
            command = f'cd /root/Desktop/TOOLs/lfimap/; ' \
                      f'python lfimap.py -F {filepath} -a'
            stream = os.popen(command)
            bash_outputs = stream.readlines()
            if any('Try specifying parameter --http-ok 404' in line for line in bash_outputs):
                new_cmd = f'{command} --http-ok 404'
                stream = os.popen(new_cmd)
                bash_outputs = stream.readlines()
            elif any('Try specifying parameter --http-ok 200' in line for line in bash_outputs):
                new_cmd = f'{command} --http-ok 200'
                stream = os.popen(new_cmd)
                bash_outputs = stream.readlines()

            os.remove(filepath)

            result = set()
            for line in bash_outputs:
                if '[+]' in line:
                    result.add(line)

            self._cache_manager.save_result(result)

        print(f'[{datetime.now().strftime("%H:%M:%S")}]: Lfimap found {len(result)} items')

    def __create_pwn_payloads(self, get_dtos: List[GetRequestDTO], start_url: str) -> set:
        checked_urls = set()
        result = set()

        parsed_parts = urlparse.urlparse(start_url)
        result.add(f'{parsed_parts.scheme}://{parsed_parts.netloc}/PWN')

        for dto in get_dtos:

            is_added = self.__check_if_added(dto.url)
            if is_added:
                continue
            target_params = filter(None, (f'{target_param}=' in dto.url for target_param in self._target_url_params))
            for tp in target_params:
                if tp in checked_urls:
                    continue
                main_url_split = dto.url.split(f'{tp}=')
                if len(main_url_split) == 1:
                    result.add(f'{main_url_split[0]}{tp}=PWN')
                elif len(main_url_split) > 1:
                    sub_url_split = main_url_split[1].split('&', 1)
                    if len(sub_url_split) == 1:
                        result.add(f'{main_url_split[0]}{tp}=PWN')
                    elif len(sub_url_split) > 1:
                        result.add(f'{main_url_split[0]}{tp}=PWN&{sub_url_split[1]}')
                checked_urls.add(tp)
        return result

    def __check_if_added(self, url):
        is_already_added = False
        parsed = urlparse.urlparse(url)
        params_to_check = filter(None, parsed.query.split("&"))
        key_to_check = ''
        for param_to_check in params_to_check:
            param_value_split = param_to_check.split('=')
            key_to_check += f'{param_value_split[0]};'

        added_path = self._already_added_pathes.get(parsed.path)
        if added_path:
            if key_to_check in added_path:
                is_already_added = True
            else:
                self._already_added_pathes[parsed.path].append(key_to_check)
        else:
            self._already_added_pathes[parsed.path] = [key_to_check]

        return is_already_added

    def __create_payloads_file(self, pwn_payloads):
        txt_filepath = f"{self._tool_result_dir}/{self._domain}.txt"
        if os.path.exists(txt_filepath):
            print(f"File found: {txt_filepath}")
            return txt_filepath

        txt_file = open(txt_filepath, 'w')
        for payload in pwn_payloads:
            txt_file.write(f"{payload}\n")
        txt_file.close()

        return txt_filepath
