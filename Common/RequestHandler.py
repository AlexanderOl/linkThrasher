from urllib.parse import urlparse

import requests
from requests.exceptions import SSLError, Timeout, ConnectionError


class RequestHandler:
    def __init__(self, cookies='', headers={}):
        self._cookies = cookies
        self._headers = headers

    def send_head_request(self, url, timeout=3):
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print(f'{url} - url is not valid')
                return
            head_response = requests.head(url, headers=self._headers, cookies=self._cookies, timeout=timeout)
            if 300 <= head_response.status_code < 400:
                if 'Location' in head_response.headers:
                    redirect = head_response.headers['Location']
                    if redirect[0] == '/':
                        redirect_url = f'{parsed.scheme}://{parsed.netloc}{redirect}'
                    else:
                        redirect_url = redirect
                    head_response = requests.head(redirect_url, headers=self._headers, cookies=self._cookies, timeout=timeout)
            if 'Content-Type' in head_response.headers \
                    and head_response.headers['Content-Type'] == 'application/octet-stream':
                print(f'Url: ({url}) content type - application/octet-stream')
                return
            return head_response
        except Exception as inst:
            print(f'Url ({url}) - Exception: {inst}')
            return

    def handle_request(self, url, post_data=None, except_ssl_action=None, except_ssl_action_args: [] = None,
                       timeout=10):

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print(f'{url} - url is not valid')
                return
            if post_data:
                response = requests.post(url,
                                         data=post_data,
                                         headers=self._headers,
                                         cookies=self._cookies,
                                         allow_redirects=False,
                                         verify=False,
                                         timeout=timeout)
            else:
                response = requests.get(url,
                                        headers=self._headers,
                                        cookies=self._cookies,
                                        allow_redirects=False,
                                        verify=False,
                                        timeout=timeout)

            if len(response.text) > 1000000:
                print(f'Url: ({url}) response too long')
                return

            return response

        except SSLError:
            if except_ssl_action_args:
                return except_ssl_action(except_ssl_action_args)
        except (ConnectionError, Timeout):
            return
        except Exception as inst:
            print(f'Url ({url}) - Exception: {inst}')
            return
