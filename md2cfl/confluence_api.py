# md2cfl - MagicDraw to Confluence importer
# Copyright (C) 2022  Archimedes Exhibitions GmbH
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import json
import logging

import requests


logger = logging.getLogger(__name__)


LIMIT_ENTRIES = 1000


class APIError(Exception):
    pass


class ConfluenceAPI:
    def __init__(self, user, password, base_url):
        self._user = user
        self._password = password
        self._base_url = base_url if base_url[-1] == '/' else base_url + '/'

    def create_page(self, parent_id, title, body):
        parent_info = self.get_page_info(parent_id)

        logger.debug(f'Creating new page under space={parent_info["space"]["key"]}')

        payload = {
            'title': title,
            'type': 'page',
            'space': {
                'key': parent_info['space']['key']
            },
            'ancestors': [
                {'id': parent_id},
            ],
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            }
        }
        r = self._perform_json_request('POST',
                                       path='/content',
                                       data=payload)

        logger.debug(f'Created new page result={r}')

        return r

    def get_space_key(self, page_id):
        return self.get_page_info(page_id)['space']['key']

    def get_page_by_name(self, space_key, name):
        payload = {
            'title': name,
            'spaceKey': space_key,
        }

        r = self._perform_request('GET',
                                  path=f'/content',
                                  params=payload)

        return r.json()

    def get_property(self, page_id, key):
        r = self._perform_request('GET',
                                  path=f'/content/{page_id}/property/{key}',
                                  raise_exception=False)

        if r.status_code == 404:
            return None
        else:
            return r.json()

    def delete_page(self, page_id):
        r = self._perform_request('DELETE',
                                  path=f'/content/{page_id}',
                                  raise_exception=False)

        return r.status_code in (200, 204)

    def get_children(self, page_id):
        r = self._perform_request('GET',
                                  path=f'/content/{page_id}/child/page',
                                  params={'limit': LIMIT_ENTRIES})

        return r.json()

    def set_property(self, page_id, key, value):
        prop = self.get_property(page_id, key)

        if prop is None:
            payload = {
                'key': key,
                'value': value
            }

            r = self._perform_json_request('POST',
                                           path=f'/content/{page_id}/property/{key}',
                                           data=payload)
        else:
            payload = {
                'id': prop['id'],
                'key': key,
                'value': value,
                'version': {
                    'number': prop['version']['number'] + 1,
                    'minorEdit': True
                }
            }

            r = self._perform_json_request('PUT',
                                           path=f'/content/{page_id}/property/{key}',
                                           data=payload)

        return r

    def get_last_updated(self, content_id):
        r = self._perform_request('GET',
                                  path=f'/content/{content_id}/history')

        return r.json()['lastUpdated']['when']

    def get_attachments(self, page_id):
        attachments = {}
        r = self._perform_request('GET',
                                  path=f'/content/{page_id}/child/attachment')

        results = r.json()['results']
        for result in results:
            last_updated = self.get_last_updated(result['id'])

            attachments[result['title']] = {'id': result['id'], 'last_updated': last_updated}

        return attachments

    def upload_attachment(self, page_id, filepath, comment=None):
        attachments = self.get_attachments(page_id)
        filename = os.path.basename(filepath)

        if filename in attachments.keys():
            urlpath = f'/content/{page_id}/child/attachment/{attachments[filename]["id"]}/data'
            logger.debug(f'Last updated: {attachments[filename]["last_updated"]}')
        else:
            urlpath = f'/content/{page_id}/child/attachment'
            logger.debug('New file')

        r = self._perform_request('POST',
                                  path=urlpath,
                                  headers={'X-Atlassian-Token': 'no-check'},
                                  data={'comment': comment, 'minorEdit': 'false'},
                                  files={'file': open(filepath, 'rb')})

        logger.debug(f'Upload file={filename} to page_id={page_id} result={r.status_code}')

        return r.json()

    def get_page_info(self, page_id):
        r = self._perform_request('GET',
                                  path=f'/content/{page_id}')

        return r.json()

    def get_page_body(self, page_id):
        r = self._perform_request('GET',
                                  path=f'/content/{page_id}',
                                  params={'expand': 'body.storage'})

        return r.json()['body']['storage']['value']

    def update_page(self, page_id, title, body):
        page_info = self.get_page_info(page_id)

        version_number = page_info['version']['number'] + 1

        logger.debug(f'Updating page id={page_id} title={title} new version={version_number}')

        payload = {
            'id': page_id,
            'type': 'page',
            'title': title,
            'version': {'number': version_number},
            'body': {'storage':
                         {'value': body,
                          'representation': 'storage'}}
        }

        reply = self._perform_json_request('PUT',
                                           path=f'/content/{page_id}',
                                           data=payload)

        logger.debug(f'Page updated successfully (reply={reply})')

        return reply

    def set_labels(self, page_id, labels):
        labels_dicts = [{'prefix': 'global', 'name': label} for label in labels]

        reply = self._perform_json_request('POST',
                                           path=f'/content/{page_id}/label',
                                           data=labels_dicts)

        logger.debug(f'Added labels {labels} to page id={page_id} (reply={reply})')

        return reply

    def set_page_restrictions(self, page_id):
        payload = [
            {
                'operation': 'update',
                'restrictions': {
                    'user': [
                        {
                            'type': 'known',
                            'username': self._user
                        }
                    ]
                }
            }
        ]

        reply = self._perform_json_request('PUT',
                                           path=f'/content/{page_id}/restriction',
                                           data=payload,
                                           experimental_api=True)

        logger.debug(f'Setting page restriction to page id={page_id} for user={self._user} '
                     f'(reply={reply}')

        return reply

    def _perform_request(self, method, path, headers=None, data=None, raise_exception=True,
                         experimental_api=False, **kwargs):
        if experimental_api:
            url = self._base_url + 'rest/experimental' + path
        else:
            url = self._base_url + 'rest/api' + path

        r = requests.request(method, url=url, auth=(self._user, self._password), headers=headers, data=data, **kwargs)

        if r.status_code == 200 or not raise_exception:
            return r
        else:
            raise APIError(f'Error code={r.status_code} url={url} text={r.text}')

    def _perform_json_request(self, method, path, data=None, raise_exception=True, experimental_api=False, **kwargs):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        r = self._perform_request(method, path, headers=headers, data=json.dumps(data),
                                  raise_exception=raise_exception, experimental_api=experimental_api)

        return r.json()


def create():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--user', '-u', default=os.environ.get('USERNAME'))
    parser.add_argument('--password', '-p', default=os.environ.get('PASSWORD'))
    parser.add_argument('--url', default='https://confluence.archimedes-exhibitions.de/')

    args = parser.parse_args()

    return ConfluenceAPI(user=args.user,
                         password=args.password,
                         base_url=args.url)
