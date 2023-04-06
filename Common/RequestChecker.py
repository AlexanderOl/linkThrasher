from urllib.parse import urlparse


class RequestChecker:
    def __init__(self):
        self._checked_routes = set()
        self._checked_get_params = set()
        self._checked_form_params = set()

    def is_route_checked(self, url, url_part) -> bool:
        parsed = urlparse(url)
        key = f'{parsed.netloc};{url_part}'
        if key not in self._checked_routes:
            self._checked_routes.add(key)
            return False
        return True

    def is_get_param_checked(self, original_url, param_k_v) -> bool:
        if '=' not in param_k_v:
            print(f'Url: {original_url} query param without "=" {param_k_v}')
            return True
        main_url_split = original_url.split(param_k_v)
        key = f'{main_url_split[0]};{param_k_v}'
        if key not in self._checked_get_params:
            self._checked_get_params.add(key)
            return False
        return True

    def is_form_param_checked(self, method_type, url, param) -> bool:
        parsed = urlparse(url)
        key = f'{method_type};{parsed.netloc};{parsed.path};{param}'
        if key not in self._checked_form_params:
            self._checked_form_params.add(key)
            return False
        return True
