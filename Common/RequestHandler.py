import inject
import requests
from requests import Response
from urllib.parse import urlparse
from requests.exceptions import SSLError, Timeout, ConnectionError
from urllib3 import exceptions, disable_warnings

from Common.Logger import Logger
from Helpers.CookieHelper import CookieHelper
from Models.Constants import HEADERS


class RequestHandler:

    def __init__(self):
        self._cookie_helper = inject.instance(CookieHelper)
        self._logger = inject.instance(Logger)

        disable_warnings(exceptions.InsecureRequestWarning)

    def send_head_request(self, url, except_ssl_action=None,
                          except_ssl_action_args: [] = None,
                          timeout=3):
        try:
            parsed = urlparse(url)
            cookies = self._cookie_helper.get_cookies_dict(parsed.netloc)
            if not parsed.scheme or not parsed.netloc:
                self._logger.log_warn(f'{url} - url is not valid')
                return

            head_response = self.__send_prepared_request('HEAD', url, {}, timeout, cookies)
            if 300 <= head_response.status_code < 400:
                if 'Location' in head_response.headers:
                    redirect = head_response.headers['Location']
                    if redirect[0] == '/':
                        redirect_url = f'{parsed.scheme}://{parsed.netloc}{redirect}'
                    else:
                        redirect_url = redirect
                    head_response = self.__send_prepared_request('HEAD',
                                                                 redirect_url, {},
                                                                 timeout, cookies)
            if 'Content-Type' in head_response.headers and \
                    (head_response.headers['Content-Type'] == 'application/octet-stream' or
                     head_response.headers['Content-Type'] == 'application/x-gzip' or
                     head_response.headers['Content-Type'] == 'video/mp4'):
                self._logger.log_warn(f'Url ({url}) content type - {head_response.headers["Content-Type"]}')
                return
            if 'content-disposition' in head_response.headers \
                    and 'attachment' in head_response.headers['content-disposition']:
                self._logger.log_warn(f'Url: ({url}) '
                                      f'content-disposition - {head_response.headers["content-disposition"]}')
                return
            return head_response
        except SSLError:
            if except_ssl_action_args:
                return except_ssl_action(except_ssl_action_args)
        except (ConnectionError, Timeout):
            self._logger.log_warn(f'Url ({url}) - Timeout, ConnectionError')
            return
        except Exception as inst:
            self._logger.log_error(f'Url ({url}) - Exception: {inst}')
            return

    def handle_request(self, url: str, post_data=None, except_ssl_action=None, except_ssl_action_args: [] = None,
                       timeout=10):

        try:
            parsed = urlparse(url)
            cookies = self._cookie_helper.get_cookies_dict(parsed.netloc)
            if not parsed.scheme or not parsed.netloc:
                self._logger.log_warn(f'{url} - url is not valid')
                return

            if post_data:
                response = self.__send_prepared_request('POST', url, post_data, timeout, cookies)
            else:
                response = self.__send_prepared_request('GET', url, {}, timeout, cookies)

            if len(response.text) > 5000000:
                self._logger.log_warn(f'Url ({url}) response too long')
                return

            return response

        except SSLError:
            if except_ssl_action_args:
                return except_ssl_action(except_ssl_action_args)
        except (ConnectionError, Timeout):
            return
        except Exception as inst:
            self._logger.log_error(f'Url ({url}) - Exception: {inst}')
            return

    def __send_prepared_request(self, method, url, post_data, timeout, cookie) -> Response:
        s = requests.Session()
        req = requests.Request(method=method,
                               url=url,
                               headers=HEADERS,
                               cookies=cookie,
                               data=post_data)

        prep = req.prepare()
        prep.url = url
        response = s.send(prep, verify=False, timeout=timeout)

        self._logger.log_info(f'URL: {url}, METHOD: {method}, STATUS: {response.status_code}', )
        self._logger.log_debug(f'URL: {url}, METHOD: {method}, STATUS: {response.status_code}', )

        return response
