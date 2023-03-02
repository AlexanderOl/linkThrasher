import os
import pathlib
import time
from typing import List
from urllib.parse import urlparse

from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO


class Nmap:
    def __init__(self, domain, headers, cookies=''):
        self._tool_name = self.__class__.__name__
        self._domain = domain
        self._cache_manager = CacheManager(self._tool_name, self._domain)
        self._request_handler = RequestHandler(headers, cookies)

    def check_ports(self, get_dtos: List[GetRequestDTO]):
        subdomains = list((urlparse(dto.url).netloc for dto in get_dtos))

        port_get_dtos = self._cache_manager.get_saved_result()
        if not port_get_dtos:
            start = time.time()

            bash_outputs = self.__run_nmap_command(subdomains)
            url_with_ports = self.__get_url_with_ports(bash_outputs)

            port_get_dtos = self.__check_urls_with_ports(url_with_ports, get_dtos)

            self._cache_manager.save_result(port_get_dtos)

            end = time.time()
            print(f'Nmap finished in {(end - start) / 60} minutes')

        return port_get_dtos

    def __get_url_with_ports(self, bash_outputs: List[str]) -> set:

        url_with_ports = set()
        current_domain = ''
        for line in bash_outputs:

            if line.startswith('Nmap scan report for '):
                current_domain = line.split('Nmap scan report for ', 1)[1].split(' ', 1)[0]
            elif ' open ' in line:
                port = line.split('/', 1)[0]
                url_with_ports.add(f'https://{current_domain}:{port}/')

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

    def __check_urls_with_ports(self, url_with_ports, get_dtos: List[GetRequestDTO]) -> List[GetRequestDTO]:
        result: List[GetRequestDTO] = []
        for url in url_with_ports:
            response = self._request_handler.handle_request(url,
                                                            except_ssl_action=self.__except_ssl_action,
                                                            except_ssl_action_args=[url])
            if response is not None:
                resp_length = len(response.text)
                netloc = urlparse(url).netloc
                if not any(dto for dto in get_dtos if netloc in dto.url and dto.response_length != resp_length) and \
                        not any(dto for dto in result if netloc in dto.url and dto.response_length != resp_length):
                    result.append(GetRequestDTO(url, response))

        return result

    def __except_ssl_action(self, args: []):
        target_url = args[0]
        if target_url.startswith('http:'):
            return
        target_url = target_url.replace('https:', 'http:')
        return self._request_handler.handle_request(target_url)
