import os
import urllib
import urllib.parse as urlparse
import uuid
from copy import deepcopy
from typing import List

import inject

from Common.Logger import Logger
from Common.RequestHandler import RequestHandler
from Helpers.CacheHelper import CacheHelper
from Models.FormRequestDTO import FormRequestDTO
from Models.HeadRequestDTO import HeadRequestDTO
from Models.InjectionFoundDTO import InjectionFoundDTO, InjectionType


class SsrfManager:

    def __init__(self):
        self._ngrok_url = os.environ.get('ngrok_url')
        self._ngrok_url_safe = urllib.parse.quote(self._ngrok_url, safe='')
        self._url_params = ['url', 'redirect', 'file', 'page', 'source', 'path', 'return', 'returnto', 'return_to',
                            'checkout_url', 'continue', 'return_path', 'go', 'image_url', 'login', 'view', 'out', 'to',
                            'window', 'data', 'reference', 'site', 'html', 'val', 'validate', 'domain', 'callback',
                            'feed', 'host', 'port', 'dir', 'next', 'target', 'rurl', 'dest', 'destination', 'redir',
                            'redirect_uri', 'redirect_url']
        self._tool_dir = f'Results/SsrfManager'
        self._logger = inject.instance(Logger)
        self._request_handler = inject.instance(RequestHandler)

    def check_get_requests(self, domain: str, dtos: List[HeadRequestDTO]):

        if not os.path.exists(self._tool_dir):
            os.makedirs(self._tool_dir)

        get_domain_log = f'{self._tool_dir}/GET_{domain.replace(":", "_")}_uids.txt'
        if not os.path.exists(get_domain_log):
            cache_manager = CacheHelper('SsrfManager/Get', domain, 'Results')
            results: List[InjectionFoundDTO] = []
            for dto in dtos:
                self.__check_route_params(domain, dto.url, results)
            cache_manager.save_dtos(results)

    def check_form_requests(self, domain: str, form_results: List[FormRequestDTO]):
        form_domain_log = f'{self._tool_dir}/FORM_{domain.replace(":", "_")}_uids.txt'
        if not os.path.exists(form_domain_log):
            cache_manager = CacheHelper('SsrfManager/Form', domain, 'Results')
            results: List[InjectionFoundDTO] = []
            for item in form_results:
                self.__send_ssrf_form_request(domain, item, results)
            cache_manager.save_dtos(results)

    def __check_route_params(self, domain: str, url, results: List[InjectionFoundDTO]):
        payloads_urls = set()
        parsed = urlparse.urlparse(url)
        queries = [s for s in parsed.query.split("&") if any(xs in str(s).lower() for xs in self._url_params)]

        for query in queries:
            payload = self.__get_url_ngrok_payload(domain, url, str(query))
            payloads_urls.add(payload)

        for url in payloads_urls:
            response = self._request_handler.handle_request(url)
            if response is not None and \
                    str(response.status_code).startswith('3') \
                    and 'Location' in response.headers \
                    and response.headers['Location'].startswith(self._ngrok_url):
                msg = f'OPEN REDIRECT in GET FOUND! url: {url}'
                self._logger.log_warn(msg)
                results.append(
                    InjectionFoundDTO(InjectionType.Open_Redirect_PostForm, url, self._ngrok_url_safe, response.text, msg))

    def __get_url_ngrok_payload(self, domain: str, url: str, query: str):
        param_split = query.split('=')
        main_url_split = url.split(query)
        uid_str = str(uuid.uuid4())[0:8]
        payload = main_url_split[0] + param_split[0] + f'={self._ngrok_url_safe}/{uid_str}' + main_url_split[1]
        get_domain_log = f'{self._tool_dir}/GET_{domain.replace(":", "_")}_uids.txt'
        with open(get_domain_log, 'a') as f:
            f.write(f'{uid_str}:{payload}\n')
        return payload

    def __get_param_ngrok_payload(self, domain: str, url: str, param: str, method_type: str):
        uid_str = str(uuid.uuid4())[0:8]
        payload = f'{self._ngrok_url_safe}/{uid_str}'
        get_domain_log = f'{self._tool_dir}/GET_{domain.replace(":", "_")}_uids.txt'
        with open(get_domain_log, 'a') as f:
            f.write(f'{uid_str}:{url}:{param}:{method_type}\n')
        return payload

    def __send_ssrf_form_request(self, domain: str, dto: FormRequestDTO, results: List[InjectionFoundDTO]):
        try:
            for form in dto.form_params:
                if form.method_type == "POST":
                    for param in form.params:
                        if any(s in str(param).lower() for s in self._url_params) or \
                                str(form.params[param]).startswith('/') or \
                                str(form.params[param]).startswith('%2F') or \
                                str(form.params[param]).startswith('http'):
                            payload = deepcopy(form.params)
                            payload[param] = self.__get_param_ngrok_payload(domain, dto.url, param, "POST")

                            response = self._request_handler.handle_request(dto.url, post_data=payload)
                            if response is not None and \
                                    str(response.status_code).startswith('3') \
                                    and 'Location' in response.headers \
                                    and response.headers['Location'].startswith(self._ngrok_url):
                                msg = f'OPEN REDIRECT in POST FOUND! param: {param}, url: {dto.url}'
                                self._logger.log_warn(msg)
                                results.append(InjectionFoundDTO(InjectionType.Open_Redirect_PostForm, dto.url, param,
                                                                 response.text, msg))

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
                        if any(s in str(param).lower() for s in self._url_params) or \
                                str(form.params[param]).startswith('/') or \
                                str(form.params[param]).startswith('%2F') or \
                                str(form.params[param]).startswith('http'):
                            payload = self.__get_param_ngrok_payload(domain, dto.url, param, "POST")
                            prev_url = url
                            url += (param + f'={payload}&')

                            response = self._request_handler.handle_request(url)
                            if response is not None \
                                    and str(response.status_code).startswith('3') \
                                    and 'Location' in response.headers \
                                    and response.headers['Location'].startswith(self._ngrok_url):
                                msg = f'OPEN REDIRECT in GET FOUND! param: {param}, url: {dto.url}'
                                self._logger.log_warn(msg)
                                results.append(
                                    InjectionFoundDTO(InjectionType.Open_Redirect_Get, dto.url, param, response.text, msg))
                            if response is not None and response.status_code == 400:
                                url = prev_url
                else:
                    self._logger.log_warn("METHOD TYPE NOT FOUND: " + form.method_type)
                    return
        except Exception as inst:
            self._logger.log_error(f"Exception - ({dto.url}) - {inst}")
