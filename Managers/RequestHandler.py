import requests


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
                                         verify=False,
                                         timeout=timeout)
            else:
                response = requests.get(url,
                                        headers=self._headers,
                                        cookies=self._cookies,
                                        verify=False,
                                        timeout=timeout)
            return response

        except requests.exceptions.SSLError:
            if except_ssl_action_args:
                return except_ssl_action(except_ssl_action_args)
        except requests.exceptions.ConnectionError:
            return
        except Exception as inst:
            print(f'Url ({url}) - Exception: {inst}')
            return
