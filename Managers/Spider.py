import requests
import re
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from Managers.CacheManager import CacheManager
from Models.GetRequestDTO import GetRequestDTO
from Models.FormRequestDTO import FormRequestDTO, FormDetailsDTO


class Spider:
    def __init__(self, current_domain, cookies, headers, max_depth, main_domain):
        self._current_domain = current_domain
        self._main_domain = main_domain
        self._cookies = cookies
        self._headers = headers
        self._max_depth = int(max_depth)
        self._social_media = ["facebook", "twitter", "linkedin", "youtube", "google", "cdn-cgi", "intercom",
                              "atlassian",
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

        target_url = self.__check_target_url(target_url)
        if not target_url:
            return

        try:
            response = requests.get(target_url, headers=self._headers, cookies=self._cookies, verify=False)

            print(f'Url ({target_url}) - status code:{response.status_code}, length: {len(response.text)}')

            if response.headers['Content-Type'] in self._ignore_content_types:
                self._file_get_DTOs.append(GetRequestDTO(target_url, response))
                return

            if len(self._get_DTOs) > 0:
                if any(dto for dto in self._get_DTOs if
                       dto.response_length == len(response.text) and
                       dto.status_code == response.status_code and
                       dto.content_type == response.headers['Content-Type']):
                    return

            if response.status_code < 300 and len(response.history) <= 2:
                web_page = response.text
                dto = GetRequestDTO(target_url, response)
                self._get_DTOs.append(dto)
                self.__get_forms(target_url, web_page)
            else:
                return
        except requests.exceptions.SSLError:
            if target_url.startswith('http:'):
                return
            print(f'Url ({target_url}) - SSLError')
            target_url = target_url.replace('https:', 'http:')
            self.__recursive_search(target_url, current_depth)
            return
        except Exception as inst:
            print(f'Url ({target_url}) - Exception: {inst}')
            return

        href_for_search = self.__get_href_for_search(web_page, target_url)

        for item in href_for_search:
            self.__recursive_search(item, current_depth)

    def __get_forms(self, target_url, web_page):
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
                        params[param_name] = default_value
                form_details.append(FormDetailsDTO(action_tag, params, method))
            self._form_DTOs.append(FormRequestDTO(target_url, form_details))

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
                    and ':' not in href:
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

        if self._url_ignore_ext_regex.search(parsed.query):
            self._file_get_DTOs.append(GetRequestDTO(url))
            return

        return url

    def __get_href_for_search(self, web_page, target_url):
        self._checked_urls.add(target_url)
        href_list = set()
        urls = BeautifulSoup(web_page, "html.parser").findAll('a')
        url_parts = urlparse(target_url)
        main_url = f"{url_parts.scheme}://{url_parts.hostname}"
        for url in urls:
            try:
                href = url.get('href')
                is_valid_href = self.__check_href(href, target_url)
                if is_valid_href:
                    if href[0] == '/':
                        href_list.add(main_url + href)
                    elif str(href[0:4]) == "http":
                        href_list.add(href)
                    else:
                        href_list.add(f'{main_url}/{href}')
            except Exception as inst:
                print(inst)

        dict_href = {}
        for found_href in href_list:
            parsed = urlparse(found_href)
            dict_href[f'{parsed[0]}{parsed[1]}{parsed[2]}'] = found_href

        return set(dict_href.values())