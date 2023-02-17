from datetime import timedelta

import requests
from requests import Response


class RequestHandler:
    def __init__(self, cookies, headers):
        self._cookies = cookies
        self._headers = headers

    def handle_request(self, url, post_data=None, except_ssl_action=None, except_ssl_action_args: [] = None,
                       timeout=10):

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
            return
        except requests.exceptions.Timeout:
            response = Response()
            response.elapsed = timedelta(seconds=timeout)
            print(f'Url ({url}) - Timeout occurred')
            return response
        except Exception as inst:
            print(f'Url ({url}) - Exception: {inst}')
            return
