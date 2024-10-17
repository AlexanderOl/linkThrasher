import os
import pathlib
import inject

from urllib.parse import urlparse
from Common.Logger import Logger
from Helpers.CacheHelper import CacheHelper
from Models.Constants import URL_IGNORE_EXT_REGEX, SOCIAL_MEDIA


class LinkFinder:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_cache_result_path")}{self._tool_name}'
        self._black_list = ["application/", "text/", "image/", "mm/dd/yyyy", "yyyy/mm/dd", "dd/m/yyyy", "mm/d/yyyy",
                            "request/", "dojo/", "audio/", "video/", "font/", "/x-icon"]
        self._logger = inject.instance(Logger)

    def get_urls_from_js(self, all_urls: set[str], start_url) -> set[str]:

        domain = urlparse(start_url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        result = cache_manager.get_saved_result()

        if not result and not isinstance(result, set):
            result = self.__search_urls_in_js(all_urls, start_url)
            cache_manager.cache_result(result)

        self._logger.log_info(f'({domain}) {self._tool_name} found {len(result)} items')
        return result

    def __search_urls_in_js(self, all_urls: set[str], start_url: str) -> set[str]:
        domain = urlparse(start_url).netloc

        script_urls = [line for line in all_urls if urlparse(line).path.endswith('.js') and
                       all(word not in line for word in SOCIAL_MEDIA)]

        result = set()
        if len(script_urls) == 0:
            return result

        tool_directory = f"{self._tool_result_dir}/{domain}"
        if not os.path.exists(tool_directory):
            os.makedirs(tool_directory)

        domain_tool_directory_path = os.path.join(pathlib.Path().resolve(), tool_directory)
        for url in script_urls:
            command = f'cd {domain_tool_directory_path}; wget {url} -q --timeout=20 --tries=2'
            stream = os.popen(command)
            stream.read()

        command = f'cd /root/Desktop/TOOLs/LinkFinder; ' \
                  f'python linkfinder.py -i "{domain_tool_directory_path}/*" -o cli'
        stream = os.popen(command)
        bash_outputs = stream.readlines()

        for found in set([x.lower() for x in bash_outputs]):
            if 'linkfinder.py' in found:
                break
            if URL_IGNORE_EXT_REGEX.search(found) or 'mailto:' in found:
                continue
            if found.startswith('./'):
                found = found[2:]
            if found.endswith('\n'):
                found = found[:-2]
            if not any(word in found for word in self._black_list):
                if found.startswith('http'):
                    if domain in found:
                        result.add(found)
                    else:
                        continue
                elif not found:
                    continue
                elif found[0] == '/':
                    result.add(f'{start_url.rstrip("/")}/{found[1:]}')
                else:
                    result.add(f'{start_url}/{found}')

        # shutil.rmtree(tool_directory, ignore_errors=True)

        self._logger.log_info(f'({domain}) {self._tool_name} finished')
        return result
