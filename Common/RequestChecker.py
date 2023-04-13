from copy import deepcopy
from typing import List
from urllib.parse import urlparse


class RequestChecker:
    def __init__(self):
        self._checked_routes = set()
        self._checked_get_params = set()
        self._checked_form_params = set()

    def get_route_payloads(self, url: str, injections: []) -> List[str]:
        parsed = urlparse(url)
        route_parts = [r for r in parsed.path.split('/') if r.strip()]
        route_url_payloads = []

        for index, part in enumerate(route_parts):

            if self.is_route_checked(url, part):
                continue

            for injection in injections:
                payload_part = f'{part}{injection}'
                new_route_parts = deepcopy(route_parts)
                new_route_parts[index] = payload_part
                new_url = f'{parsed.scheme}://{parsed.netloc}/{"/".join(new_route_parts)}?{parsed.query}'
                route_url_payloads.append(new_url)

        return route_url_payloads

    def is_route_checked(self, url, url_part) -> bool:
        parsed = urlparse(url)
        key = f'{parsed.netloc};{url_part}'
        if key not in self._checked_routes:
            self._checked_routes.add(key)
            return False
        return True

    def get_param_payloads(self, url: str, injections: []) -> set:
        payloads_urls = set()
        parsed = urlparse(url)
        param_key_values = filter(None, parsed.query.split("&"))

        for param_k_v in param_key_values:

            if self.is_get_param_checked(url, param_k_v):
                continue

            main_url_split = url.split(param_k_v)
            param_key = param_k_v.split('=')[0]
            for exp in injections:
                payloads_urls.add(f'{main_url_split[0]}{param_key}={exp}{main_url_split[1]}')

        return payloads_urls

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
