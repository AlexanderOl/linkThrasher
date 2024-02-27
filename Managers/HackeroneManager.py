import os

import requests
import json

from Managers.DomainManager import DomainManager
from Managers.UrlListManager import UrlListManager

query_url = "https://hackerone.com/programs/search?query=type:hackerone&sort=published_at:descending&page={page}"

policy_scope_query = """
query PolicySearchStructuredScopesQuery($handle: String!) {
  team(handle: $handle) {
    structured_scopes_search {
      nodes {
        ... on StructuredScopeDocument {
          identifier
          eligible_for_bounty
          eligible_for_submission
          display_name
          instruction
        }
      }
    }
  }
}
"""

scope_query = """
query TeamAssets($handle: String!) {
  team(handle: $handle) {
    in_scope_assets: structured_scopes(
      archived: false
      eligible_for_submission: true
    ) {
      edges {
        node {
          asset_identifier
          asset_type
          eligible_for_bounty
        }
      }
    }
  }
}
"""


class HackeroneManager:
    def __init__(self, headers):
        self._headers = headers
        self._max_program_count = int(os.environ.get("h1_program_count"))

    def run(self):
        targets = self.__hackerone_to_list()

        urls = set([target for target in targets if target.startswith('http')])
        if len(urls) > 0:
            multiple_man = UrlListManager(self._headers)
            multiple_man.run(urls)

        domains = set([target.replace('*.', '') for target in targets if not target.startswith('http')])
        domain_man = DomainManager(self._headers)
        for domain in domains:
            domain_man.check_domain(domain)

    def __hackerone_to_list(self) -> [str]:
        targets = {'domains': [], 'with_bounty': []}
        page = 1
        program_count = 0
        with requests.Session() as session:
            while True:

                r = session.get(query_url.format(page=page))
                page += 1
                if r.status_code != 200:
                    break
                resp = json.loads(r.text)
                for program in resp['results']:

                    if program_count > self._max_program_count:
                        break
                    else:
                        program_count += 1

                    r = session.get("https://hackerone.com{program}".format(
                        program=program['url']),
                        headers={'Accept': 'application/json'})
                    if r.status_code != 200:
                        print('unable to retrieve %s', program['name'])
                        continue

                    resp = json.loads(r.text)
                    print('policy scope ', resp['handle'])

                    query = json.dumps({'query': policy_scope_query,
                                        'variables': {'handle': resp['handle']}})
                    r = session.post("https://hackerone.com/graphql",
                                     data=query,
                                     headers={'content-type': 'application/json'})
                    policy_scope_resp = json.loads(r.text)

                    for e in policy_scope_resp['data']['team']['structured_scopes_search']['nodes']:
                        if (e['display_name'] == 'Domain' and e['eligible_for_submission']) or \
                                (e['eligible_for_submission'] and e['identifier'].startswith('*')):
                            identifier = e['identifier']
                            for i in identifier.split(','):
                                targets['domains'].append(i)
                                bounty = e['eligible_for_bounty']
                                if bounty is True:
                                    targets['with_bounty'].append(i)

                    query = json.dumps({'query': scope_query, 'variables': {'handle': resp['handle']}})
                    r = session.post("https://hackerone.com/graphql",
                                     data=query,
                                     headers={'content-type': 'application/json'})
                    scope_resp = json.loads(r.text)
                    for e in scope_resp['data']['team']['in_scope_assets']['edges']:
                        node = e['node']
                        if node['asset_type'] == 'Domain' or node['asset_identifier'].startswith('*') \
                                or node['asset_type'] == 'URL':
                            identifier = node['asset_identifier']
                            for i in identifier.split(','):
                                targets['domains'].append(i)
                                bounty = node['eligible_for_bounty']
                                if bounty is True:
                                    targets['with_bounty'].append(i)
        return targets['with_bounty']
