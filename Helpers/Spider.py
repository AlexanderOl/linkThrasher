import os
import inject

from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from Common.Logger import Logger
from Common.RequestChecker import RequestChecker
from Helpers.CacheHelper import CacheHelper
from Common.RequestHandler import RequestHandler
from Models.Constants import SOCIAL_MEDIA, URL_IGNORE_EXT_REGEX
from Models.HeadRequestDTO import HeadRequestDTO


class Spider:
    def __init__(self):
        self._max_depth = int(os.environ.get('max_depth'))
        self._checked_urls = set()
        self._checked_hrefs = set()
        self._urls_counter = 0
        self._tool_name = self.__class__.__name__
        self._head_dtos: List[HeadRequestDTO] = []
        self._request_handler = inject.instance(RequestHandler)
        self._request_checker = inject.instance(RequestChecker)
        self._allowed_content_types = [
                    'application/json',
                    'text/plain',
                    'application/ld+json',
                    'text/html'
        ]
        self._logger = inject.instance(Logger)

    def get_all_links(self, start_url) -> List[HeadRequestDTO]:

        domain = urlparse(start_url).netloc
        cache_manager = CacheHelper(self._tool_name, domain)
        head_found = cache_manager.get_saved_result()

        if head_found is None:
            current_depth = 0
            self.__recursive_search(domain, start_url, current_depth)
            cache_manager.cache_result(self._head_dtos)
        else:
            self._head_dtos = head_found

        self._logger.log_info(f'({domain}) Spider found {len(self._head_dtos)} head_dtos')

        return self._head_dtos

    def __recursive_search(self, domain: str, target_url: str, current_depth: int):

        if current_depth >= self._max_depth:
            return
        else:
            current_depth += 1

        checked_url = self.__check_target_url(domain, target_url)
        if not checked_url:
            return

        check = self._request_handler.send_head_request(checked_url)
        if check is None:
            return

        response = self._request_handler.handle_request(url=checked_url,
                                                        except_ssl_action=self.__except_ssl_action,
                                                        except_ssl_action_args=[checked_url, current_depth, domain])
        if response is None:
            return

        web_page = response.text
        if 300 <= response.status_code < 400:
            if 'Location' in response.headers:
                redirect = response.headers['Location']
                if redirect[0] == '/':
                    redirect_url = f"{target_url}{redirect}"
                else:
                    redirect_url = redirect
                self.__recursive_search(domain, redirect_url, current_depth - 1)
        elif response.status_code < 300 and len(response.history) <= 2:
            self._head_dtos.append(HeadRequestDTO(response))

        else:
            return

        urls_for_search = self.__get_urls_for_search(web_page, checked_url)

        for item in urls_for_search:
            self.__recursive_search(domain, item, current_depth)

    def __except_ssl_action(self, args: []):
        target_url = args[0]
        current_depth = args[1]
        domain = args[2]
        if target_url.startswith('http:'):
            return
        self._logger.log_warn(f'Url ({target_url}) - ConnectionError(SSLError)')
        target_url = target_url.replace('https:', 'http:')
        self.__recursive_search(domain, target_url, current_depth)

    def __check_href(self, href, target_url):
        result = False
        if href:
            if '#' in href:
                href = href[1:]
            if len(href) > 2 \
                    and href not in SOCIAL_MEDIA \
                    and href not in self._checked_hrefs \
                    and target_url[len(target_url) - len(href):] != href \
                    and href not in target_url \
                    and not URL_IGNORE_EXT_REGEX.search(href):
                self._checked_hrefs.add(href)
                result = True

        return result

    def __check_target_url(self, domain, url):

        parsed = urlparse(url)
        if url in self._checked_urls \
                or any(word in url for word in SOCIAL_MEDIA) \
                or domain not in parsed.netloc:
            return

        self._checked_urls.add(url)

        return url

    def __get_urls_for_search(self, web_page, target_url):

        href_urls = self.__get_url_from_html(tag='a', attr='href', web_page=web_page, target_url=target_url)
        links_urls = self.__get_url_from_html(tag='link', attr='href', web_page=web_page, target_url=target_url)
        data_url = self.__get_url_from_html(tag='div', attr='data-url', web_page=web_page, target_url=target_url)
        form_url = self.__get_url_from_html(tag='form', attr='action', web_page=web_page, target_url=target_url)
        action_urlsrc_url = self.__get_url_from_html(tag='action', attr='urlsrc', web_page=web_page, target_url=target_url)

        href_urls.update(links_urls)
        href_urls.update(data_url)
        href_urls.update(form_url)
        href_urls.update(action_urlsrc_url)
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
                href = url.get(attr)
                if not href:
                    continue
                url_part = str(href).replace(' ', '')
                is_valid_href = self.__check_href(url_part, target_url)
                if is_valid_href:
                    if url_part.startswith('/'):
                        html_urls.add(main_url + url_part)
                    elif url_part.startswith('./'):
                        html_urls.add(main_url + url_part[1:])
                    elif url_part.startswith('#'):
                        continue
                    elif url_part.startswith('http'):
                        html_urls.add(url_part)
                    elif url_part.startswith('..') or url_part.startswith('\t'):
                        html_urls.add(f'{main_url}/{url_part[2:]}')
                    else:
                        if '/' in url_part:
                            second_part = url_part.rsplit('/', 1)[1]
                            if target_url.endswith(second_part):
                                html_urls.add(f'{target_url.rsplit("/", 1)[0]}/{url_part}')
                            else:
                                html_urls.add(f'{main_url}/{url_part}')
                                self._logger.log_warn(f'Need attention ({target_url} with {url_part}). '
                                                      f'Temp result is - {main_url}/{url_part}')
                        else:
                            html_urls.add(f'{main_url}/{url_part}')
            except Exception as inst:
                self._logger.log_error(inst)

        return html_urls
