import os
import pathlib
import time
from typing import List
from urllib.parse import urlparse

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Managers.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO


class Nmap:
    def __init__(self, domain, headers, cookies=''):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._port_get_dtos: List[GetRequestDTO] = []
        self._cache_manager = CacheManager(self._tool_name, self._domain)
        self._request_handler = RequestHandler(headers, cookies)
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._existing_get_dtos: List[GetRequestDTO] = []

    def check_ports(self, get_dtos: List[GetRequestDTO]):
        subdomains = list((urlparse(dto.url).netloc for dto in get_dtos))

        self._port_get_dtos = self._cache_manager.get_saved_result()
        if not self._port_get_dtos:
            self._port_get_dtos: List[GetRequestDTO] = []
            start = time.time()

            bash_outputs = self.__run_nmap_command(subdomains)
            url_with_ports = self.__get_url_with_ports(bash_outputs)

            self._existing_get_dtos = get_dtos
            thread_man = ThreadManager()
            thread_man.run_all(self.__check_url_with_port, url_with_ports)

            self._cache_manager.save_result(self._port_get_dtos)

            end = time.time()
            print(f'Nmap finished in {(end - start) / 60} minutes')

        return self._port_get_dtos

    def __get_url_with_ports(self, bash_outputs: List[str]) -> set:

        url_with_ports = set()
        output_file = f'{self._tool_result_dir}/RAW_{self._domain}.txt'
        txt_file = open(output_file, 'w')
        current_domain = ''
        for line in bash_outputs:

            if line.startswith('Nmap scan report for '):
                txt_file.write(f"{line}\n")
                current_domain = line.split('Nmap scan report for ', 1)[1].split(' ', 1)[0]
            elif ' open ' in line:
                txt_file.write(f"{line}\n")
                port = line.split('/', 1)[0]
                url_with_ports.add(f'https://{current_domain}:{port}/')

        txt_file.close()
        return url_with_ports

    def __run_nmap_command(self, subdomains) -> List[str]:
        nmap_directory = f"Results/{self._tool_name}"
        if not os.path.exists(nmap_directory):
            os.makedirs(nmap_directory)
        txt_filepath = f"{nmap_directory}/{self._domain}.txt"
        txt_file = open(txt_filepath, 'a')
        for subdomain in subdomains:
            txt_file.write("%s\n" % str(subdomain))
        txt_file.close()

        subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
        command = f'nmap -sT -T4 -iL {subdomains_filepath} --top-ports 10000'
        stream = os.popen(command)
        bash_outputs = stream.readlines()
        os.remove(txt_filepath)

        return bash_outputs

    def __check_url_with_port(self, url):
        ssl_action_args = [url, False]
        response = self._request_handler.handle_request(url,
                                                        except_ssl_action=self.__except_ssl_action,
                                                        except_ssl_action_args=ssl_action_args)
        if response is not None:
            resp_length = len(response.text)
            netloc = urlparse(url).netloc
            if not any(dto for dto in self._existing_get_dtos if netloc in dto.url and dto.response_length != resp_length) and \
                    not any(dto for dto in self._port_get_dtos if netloc in dto.url and dto.response_length != resp_length):
                if ssl_action_args[1]:
                    url = url.replace('https:', 'http:')
                self._port_get_dtos.append(GetRequestDTO(url, response))

    def __except_ssl_action(self, args: []):
        target_url = args[0]
        if target_url.startswith('http:'):
            return
        args[1] = True
        target_url = target_url.replace('https:', 'http:')
        return self._request_handler.handle_request(target_url)
