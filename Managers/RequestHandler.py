from urllib.parse import urlparse

import requests


class RequestHandler:
    def __init__(self, cookies, headers):
        self._cookies = cookies
        self._headers = headers
        self._dead_hosts = set()

    def handle_request(self, url, post_data=None, except_ssl_action=None, except_ssl_action_args: [] = None,
                       timeout=10):
        parsed_parts = urlparse(url)
        base_url = f'{parsed_parts.scheme}://{parsed_parts.netloc}/'
        if base_url in self._dead_hosts:
            print(f'{base_url} is dead!')
            return

        try:
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
            return response

        except requests.exceptions.SSLError:
            if except_ssl_action_args:
                return except_ssl_action(except_ssl_action_args)
        except requests.exceptions.ConnectionError:
            self._dead_hosts.add(base_url)
            return
        except Exception as inst:
            print(f'Url ({url}) - Exception: {inst}')
            return
