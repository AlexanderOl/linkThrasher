import os
import pathlib
import time
import inject
from datetime import datetime
from typing import List
from urllib.parse import urlparse
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Nmap:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._port_head_dtos: List[HeadRequestDTO] = []
        self._port_get_dtos: List[GetRequestDTO] = []
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._existing_get_dtos: List[GetRequestDTO] = []
        self._batch_size = 5
        self._process_handler = inject.instance(ProcessHandler)
        self._request_handler = inject.instance(RequestHandler)
        self._thread_manager = inject.instance(ThreadManager)

    def check_ports(self, domain: str, get_dtos: List[HeadRequestDTO]) -> List[HeadRequestDTO]:
        subdomains = list((urlparse(dto.url).netloc for dto in get_dtos))
        cache_manager = CacheHelper(self._tool_name, domain, "Results")
        self._port_head_dtos = cache_manager.get_saved_result()
        if not self._port_head_dtos and not isinstance(self._port_head_dtos, List):
            self._port_head_dtos: List[HeadRequestDTO] = []
            start = time.time()
            bash_outputs = self.__run_nmap_command(domain, subdomains)
            url_with_ports = self.__parse_cmd_output(domain, bash_outputs)

            self._existing_get_dtos = get_dtos

            self._domain = domain
            self._thread_manager.run_all(self.__check_url_with_port, url_with_ports,
                                         debug_msg=f'{self._tool_name} ({domain})')

            cache_manager.cache_result(self._port_head_dtos)

            end = time.time()
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: Nmap finished in {(end - start) / 60} minutes. '
                  f'Found new {len(self._port_head_dtos)} dtos')

        return self._port_head_dtos

    def __parse_cmd_output(self, domain: str, bash_outputs: List[str]) -> set:

        url_with_ports = set()
        output_file = f'{self._tool_result_dir}/RAW_{domain}.txt'
        txt_file = open(output_file, 'w')
        current_domain = ''
        ips = set()
        ip_already_added = False
        for line in bash_outputs:

            if line.startswith('Nmap scan report for '):
                txt_file.write(f"{line}\n")
                current_domain = line.split('Nmap scan report for ', 1)[1].split(' ', 1)[0]
                ip = line.split('(')[0].split(')')[0]
                ip_already_added = ip in ips
                if not ip_already_added:
                    ips.add(ip)
            elif ' open ' in line and not ip_already_added:
                txt_file.write(f"{line}\n")
                port = line.split('/', 1)[0]
                if port in ['80', '443']:
                    continue
                url_with_ports.add(f'https://{current_domain}:{port}/')
        txt_file.close()

        if len(url_with_ports) == 0 and os.path.exists(output_file):
            os.remove(output_file)

        return url_with_ports

    def __run_nmap_command(self, domain: str, subdomains) -> List[str]:
        nmap_directory = f"Results/{self._tool_name}"
        if not os.path.exists(nmap_directory):
            os.makedirs(nmap_directory)
        txt_filepath = f"{nmap_directory}/{domain}.txt"
        txt_file = open(txt_filepath, 'w')
        for subdomain in subdomains:
            txt_file.write("%s\n" % str(subdomain))
        txt_file.close()
        subdomains_filepath = os.path.join(pathlib.Path().resolve(), txt_filepath)
        cmd_arr = ['nmap', '-sT', '-T4', '-iL', subdomains_filepath, '--open']
        bash_outputs = self._process_handler.run_temp_process(
            cmd_arr, f'NMAP runs for - {len(subdomains)} subs', timeout=600)
        os.remove(txt_filepath)
        return bash_outputs

    def __check_url_with_port(self, url):
        ssl_action_args = [url, False]
        response = self._request_handler.send_head_request(url,
                                                           except_ssl_action=self.__except_ssl_action,
                                                           except_ssl_action_args=ssl_action_args,
                                                           timeout=5)
        if response is not None:
            if str(response.status_code).startswith('3') and 'Location' in response.headers:
                redirect = response.headers['Location']
                if redirect[0] == '/':
                    redirect_url = f"{url}{redirect}"
                else:
                    redirect_url = redirect

                response = self._request_handler.handle_request(redirect_url,
                                                                except_ssl_action=self.__except_ssl_action,
                                                                except_ssl_action_args=ssl_action_args,
                                                                timeout=3)

            if 'Server' in response.headers and response.headers['Server'] == 'cloudflare':
                return
            if str(response.status_code).startswith('3') and 'Location' in response.headers:
                redirect = response.headers['Location']
                if redirect[0] != '/' and self._domain not in redirect:
                    return

            resp_length = len(response.text)
            netloc = str(urlparse(url).netloc.split(':', 1)[0])
            if (not any(dto for dto in self._existing_get_dtos if netloc in dto.url)
                    and not any(
                        dto for dto in self._port_get_dtos if
                        netloc in dto.url and dto.response_length != resp_length)):
                if ssl_action_args[1]:
                    url = url.replace('https:', 'http:')
                self._port_get_dtos.append(GetRequestDTO(url, response))
                self._port_head_dtos.append(HeadRequestDTO(response))

    def __except_ssl_action(self, args: []):
        target_url = args[0]
        if target_url.startswith('http:'):
            return
        args[1] = True
        target_url = target_url.replace('https:', 'http:')
        return self._request_handler.handle_request(target_url)
