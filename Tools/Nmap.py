import os
import pathlib
import queue
import time
import inject
from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlparse

from Common.Logger import Logger
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Common.ThreadManager import ThreadManager
from Models.GetRequestDTO import GetRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO


class Nmap:
    def __init__(self):
        self._tool_name = self.__class__.__name__
        self._tool_result_dir = f'{os.environ.get("app_result_path")}{self._tool_name}'
        self._batch_size = 5
        self._process_handler = inject.instance(ProcessHandler)
        self._request_handler = inject.instance(RequestHandler)
        self._thread_manager = inject.instance(ThreadManager)
        self._logger = inject.instance(Logger)

    def check_ports(self, domain: str, existing_head_dtos: List[HeadRequestDTO]) -> List[HeadRequestDTO]:
        subdomains = list((urlparse(dto.url).netloc for dto in existing_head_dtos))
        cache_manager = CacheHelper(self._tool_name, domain, "Results")
        port_head_dtos = cache_manager.get_saved_result()
        if not port_head_dtos and not isinstance(port_head_dtos, List):

            start = time.time()
            bash_outputs = self.__run_nmap_command(domain, subdomains)
            url_with_ports = self.__parse_cmd_output(domain, bash_outputs)

            port_head_queue = queue.Queue()
            port_get_queue = queue.Queue()
            self._thread_manager.run_all(self.__check_url_with_port, url_with_ports,
                                         debug_msg=f'{self._tool_name} ({domain})',
                                         args2=(port_head_queue, port_get_queue, domain, existing_head_dtos))

            port_head_dtos = list(port_head_queue.queue)

            cache_manager.cache_result(port_head_dtos)

            end = time.time()
            print(f'[{datetime.now().strftime("%H:%M:%S")}]: Nmap finished in {(end - start) / 60} minutes. '
                  f'Found new {len(port_head_dtos)} dtos')

        return port_head_dtos

    def __parse_cmd_output(self, domain: str, bash_outputs: List[str]) -> set:

        url_with_ports = set()
        output_file = f'{self._tool_result_dir}/RAW_{domain}.txt'
        txt_file = open(output_file, 'w')
        current_domain = ''
        ips = set()
        ip_already_added = False

        if len(bash_outputs) > 1000:
            self._logger.log_warn(f'Nmap ({domain}) found to many open ports - {len(bash_outputs)}')
            return url_with_ports

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
                if port in ['80', '443', '8443']:
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

    def __check_url_with_port(self, url: str, args: Tuple[queue, queue, str, List[HeadRequestDTO]]):

        domain = args[2]
        existing_head_dtos = args[3]
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
                if redirect[0] != '/' and domain not in redirect:
                    return

            get_dtos = args[1].queue
            resp_length = len(response.text)
            netloc = str(urlparse(url).netloc.split(':', 1)[0])
            if (not any(dto for dto in existing_head_dtos if netloc in dto.url)
                    and not any(
                        dto for dto in get_dtos if
                        netloc in dto.url and dto.response_length != resp_length)):
                if ssl_action_args[1]:
                    url = url.replace('https:', 'http:')
                args[1].put(GetRequestDTO(url, response))
                args[0].put(HeadRequestDTO(response))

    def __except_ssl_action(self, args: []):
        target_url = args[0]
        if target_url.startswith('http:'):
            return
        args[1] = True
        target_url = target_url.replace('https:', 'http:')
        return self._request_handler.handle_request(target_url)
