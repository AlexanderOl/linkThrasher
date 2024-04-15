import os
from urllib.parse import urlparse


def _try_parse_url(url: str):
    try:
        parsed_url = urlparse(url)
        return parsed_url
    except:
        print("Error parsing URL:", url)
        return None


class BbManager:
    def __init__(self):
        self._h1_api_key = os.environ.get("h1_api_key")
        self._h1_user = os.environ.get("h1_user")
        self._bc_session_id = os.environ.get("bc_session_id")
        self._it_id = os.environ.get("it_id")
        self._ywh_id = os.environ.get("ywh_id")
        self._app_cache_result_path = f'{os.environ.get("app_cache_result_path")}'
        self._res_file = f'{self._app_cache_result_path}{self.__class__.__name__}.txt'
        self._targets_path = os.environ.get("app_targets_path")
        self._black_list = ['github.com', 'google.com', 'immunefi.com', 'linkedin.com', 'apple.com']
        self._wildcards_match = ['.*', '[', '}', '[', '{', '|']

    def run(self):

        if not os.path.exists(self._app_cache_result_path):
            os.makedirs(self._app_cache_result_path)

        command = (f"bbscope h1 -t {self._h1_api_key} -u {self._h1_user} -b -p -o tc | "
                   f"grep -e ' URL' -e ' WILDCARD' > {self._res_file}")
        self._parse_cmd(command, '---H1---')

        command = f"bbscope bc -t {self._bc_session_id} -b -o tc | grep -e ' website' -e ' api'  > {self._res_file}"
        self._parse_cmd(command, '---BC---')

        command = f"bbscope it -t {self._it_id} -b -o tc | grep -e ' Url' > {self._res_file}"
        self._parse_cmd(command, '---Intigriti---')

        command = f"bbscope ywh -t {self._ywh_id} -b -o tc | grep -e ' web-application' -e ' api' > {self._res_file}"
        self._parse_cmd(command, '---YWH---')

        command = f"bbscope immunefi -b -o tc | grep 'websites_and_applications' > {self._res_file}"
        self._parse_cmd(command, '---IMMUNEFI---')

    def _parse_cmd(self, command: str, header_msg: str):
        stream = os.popen(command)
        stream.read()
        domains = set()
        wildcards = set()
        urls = set()
        domains.add(header_msg)
        wildcards.add(header_msg)
        urls.add(header_msg)
        text_file = open(self._res_file, 'r')
        lines = text_file.readlines()

        for line in lines:
            if any(word in line for word in self._black_list):
                print(f'IGNORED: {line}')
                continue
            split = line.split(' ', 1)[0]
            if any(word in split for word in self._wildcards_match):
                wildcards.add(split)
                continue
            if split.startswith('http'):
                if '*.' in line:
                    index = line.find('*.')
                    if index != -1:
                        domains.add(split[index + 2:].rstrip('/').replace('*', ''))
                        continue
                else:
                    parsed = _try_parse_url(split)
                    if parsed:
                        urls.add(f'{parsed.scheme}://{parsed.netloc}')
                    continue
            elif '/' in split:
                index = split.find('/')
                if index != -1:
                    split = split[:index]

            if '*.' in split:
                index = line.find('*.')
                if index != -1:
                    domain = split[index + 2:]
                else:
                    domain = split
                domains.add(domain.replace('*', ''))
            elif '.' in split:
                domains.add(split.replace('*', ''))

        if os.path.exists(self._res_file):
            os.remove(self._res_file)

        txt_file = open(f'{self._targets_path}all_domains.txt', 'w')
        for line in domains:
            txt_file.write(f"{line}\n")
        txt_file.close()

        txt_file = open(f'{self._targets_path}all_urls.txt', 'w')
        for line in urls:
            txt_file.write(f"{line}\n")
        txt_file.close()

        txt_file = open(f'{self._targets_path}all_wildcards.txt', 'w')
        for line in wildcards:
            txt_file.write(f"{line}\n")
        txt_file.close()

        print(f'CMD done - {command}')
        print(f'WILDCARD found - {len(wildcards)}')
        print(f'URL found - {len(urls)}')
        print(f'DOMAIN found - {len(domains)}')
