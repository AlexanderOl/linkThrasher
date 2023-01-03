import requests
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from Managers.CacheManager import CacheManager
from Managers.RequestHandler import RequestHandler
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO, FormDetailsDTO


class Spider:
    def __init__(self, current_domain, cookies, headers, max_depth, main_domain):
        self._current_domain = current_domain
        self._main_domain = main_domain
        self._max_depth = int(max_depth)
        self._social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "intercom", "atlassian",
                              "instagram", "github", "letgo", "yahoo"]
        self._checked_urls = set()
        self._checked_hrefs = set()
        self._urls_counter = 0

        self._form_DTOs: List[FormRequestDTO] = []
        self._get_DTOs: List[GetRequestDTO] = []
        self._file_get_DTOs: List[GetRequestDTO] = []
        self._url_ignore_ext_regex = re.compile(
            '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.ashx$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
            '|\.docx$|\.m4v$|\.pptx$|\.ppt$',
            re.IGNORECASE)
        self._ignore_content_types = [
            'audio/mpeg',
            'audio/x-ms-wma',
            'audio/vnd.rn-realaudio',
            'audio/x-wav',
            'image/gif',
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/vnd.microsoft.icon',
            'image/x-icon',
            'image/vnd.djvu',
            'video/mpeg',
            'video/mp4',
            'video/quicktime',
            'video/x-ms-wmv',
            'video/x-msvideo',
            'video/x-flv',
            'video/webm'
        ]
        self._request_handler = RequestHandler(cookies, headers)

    def get_all_links(self, start_url) -> List[GetRequestDTO]:

        form_cache_manager = CacheManager('Spider/Form', self._current_domain)
        get_cache_manager = CacheManager('Spider/Get', self._current_domain)
        get_found = get_cache_manager.get_saved_result()
        form_found = form_cache_manager.get_saved_result()

        if not get_found and not form_found:
            current_depth = 0
            self.__recursive_search(start_url, current_depth)
            get_cache_manager.save_result(self._get_DTOs)
            form_cache_manager.save_result(self._form_DTOs)
            file_cache_manager = CacheManager('Spider/File', self._current_domain)
            file_cache_manager.save_result(self._file_get_DTOs)
        else:
            self._get_DTOs = get_found
            self._form_DTOs = form_found

        print(
            f'[{datetime.now().strftime("%H:%M:%S")}]: ({self._current_domain}) '
            f'Spider found {len(self._get_DTOs)} get_dtos and {len(self._form_DTOs)} forms')
        return self._get_DTOs, self._form_DTOs

    def __recursive_search(self, target_url, current_depth):

        if current_depth >= self._max_depth:
            return
        else:
            current_depth += 1

        checked_url = self.__check_target_url(target_url)
        if not checked_url:
            return

        response = self._request_handler.handle_request(url=checked_url,
                                                        except_ssl_action=self.__except_ssl_action,
                                                        except_ssl_action_args=[checked_url, current_depth])
        if response is None:
            return

        if 'Content-Type' in response.headers and response.headers['Content-Type'] in self._ignore_content_types:
            self._file_get_DTOs.append(GetRequestDTO(checked_url, response))
            return

        if len(self._get_DTOs) > 0:
            if any(dto for dto in self._get_DTOs if
                   dto.response_length == len(response.text) and
                   dto.status_code == response.status_code):
                return

        if response.status_code < 300 and len(response.history) <= 2:
            web_page = response.text
            dto = GetRequestDTO(checked_url, response)
            self._get_DTOs.append(dto)
            self.__find_forms(checked_url, web_page, dto)
        else:
            return

        urls_for_search = self.__get_urls_for_search(web_page, checked_url)

        for item in urls_for_search:
            self.__recursive_search(item, current_depth)

    def __except_ssl_action(self, args: []):
        target_url = args[0]
        current_depth = args[1]
        if target_url.startswith('http:'):
            return
        print(f'Url ({target_url}) - ConnectionError(SSLError)')
        target_url = target_url.replace('https:', 'http:')
        self.__recursive_search(target_url, current_depth)

    def __find_forms(self, target_url, web_page, dto: GetRequestDTO):
        forms = BeautifulSoup(web_page, "html.parser").findAll('form')
        if forms:
            form_details: List[FormDetailsDTO] = []
            for form in forms:
                action_tag = BeautifulSoup(str(form), "html.parser").find('form').get('action')
                if not action_tag:
                    action_tag = target_url
                elif action_tag.startswith('http'):
                    action_tag = action_tag
                elif action_tag.startswith('/'):
                    action_tag = target_url + action_tag

                method = BeautifulSoup(str(form), "html.parser").find('form').get('method')
                method = method if method else "post"
                input_tags = BeautifulSoup(str(form), "html.parser").findAll('input')
                params = {}
                for input_tag in input_tags:
                    param_name = BeautifulSoup(str(input_tag), "html.parser").find('input').get('name')
                    if param_name:
                        default_value = BeautifulSoup(str(input_tag), "html.parser").find('input').get('value')
                        if default_value is None:
                            default_value = ''
                        params[param_name] = default_value
                form_details.append(FormDetailsDTO(action_tag, params, method))
            self._form_DTOs.append(FormRequestDTO(target_url, form_details, dto.status_code, dto.response_length))

    def __check_href(self, href, target_url):
        result = False
        if href:
            if '#' in href:
                href = href[1:]
            if len(href) > 2 \
                    and href not in self._social_media \
                    and href not in self._checked_hrefs \
                    and target_url[len(target_url) - len(href):] != href \
                    and href not in target_url \
                    and ':' not in href\
                    and not self._url_ignore_ext_regex.search(href):
                self._checked_hrefs.add(href)
                result = True

        return result

    def __check_target_url(self, url):

        if url.endswith('/'):
            url = url[:-1]

        parsed = urlparse(url)
        if url in self._checked_urls \
                or any(word in url for word in self._social_media) \
                or self._current_domain not in parsed.netloc:
            return

        return url

    def __get_urls_for_search(self, web_page, target_url):
        self._checked_urls.add(target_url)

        href_urls = self.__get_url_from_html(tag='a', attr='href', web_page=web_page, target_url=target_url)
        data_url = self.__get_url_from_html(tag='div', attr='data-url', web_page=web_page, target_url=target_url)

        href_urls.update(data_url)
        dict_href = {}
        for found_href in href_urls:
            parsed = urlparse(found_href)
            dict_href[f'{parsed[0]}{parsed[1]}{parsed[2]}'] = found_href

        return set(dict_href.values())

    def __get_url_from_html(self, tag, attr, web_page, target_url):
        html_urls = set()
        urls = BeautifulSoup(web_page, "html.parser").findAll(tag)
        url_parts = urlparse(target_url)
        main_url = f"{url_parts.scheme}://{url_parts.hostname}"

        for url in urls:
            try:
                url_part = url.get(attr)
                is_valid_href = self.__check_href(url_part, target_url)
                if is_valid_href:
                    if url_part.startswith('/'):
                        html_urls.add(main_url + url_part)
                    elif url_part.startswith('http'):
                        html_urls.add(url_part)
                    elif url_part.startswith('..'):
                        html_urls.add(f'{main_url}/{url_part[2:]}')
                    else:
                        if '/' in url_part:
                            second_part = url_part.rsplit('/', 1)[1]
                            if target_url.endswith(second_part):
                                html_urls.add(f'{target_url.rsplit("/", 1)[0]}/{url_part}')
                            else:
                                html_urls.add(f'{main_url}/{url_part}')
                                print(f'Need attention ({target_url} with {url_part}). Temp result is - {main_url}/{url_part}')
                        else:
                            html_urls.add(f'{main_url}/{url_part}')
            except Exception as inst:
                print(inst)

        return html_urls
