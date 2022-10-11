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

import logging
import os
import datetime

import dateutil.parser
from progress.bar import IncrementalBar

from md2cfl import renderer, utils
from md2cfl.confluence_api import APIError

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self, cfl, version_info, report, skip_restrictions,
                 force_updates, delete_children, print_summary):
        self._cfl = cfl
        self._version_info = version_info
        self._report = report
        self._skip_restrictions = skip_restrictions
        self._force_updates = force_updates
        self._delete_children = delete_children
        self._print_summary = print_summary
        self._summary = {}
        self._errors = []
        self._renderer = renderer.Renderer()
        self._current_bar = None

    def process(self):
        if self._print_summary:
            print(f'Starting MDImporter processing on {len(self._report)} root pages')

        for cfl_pageid, rootpage in self._report.items():
            self._process_root_page(cfl_pageid, rootpage)

        if self._print_summary:
            if any([item for v in self._summary.values() for item in v.values()]):
                maxlen = max([len(qualname) for qualname in self._summary.keys()])

                print('Updates summary:')
                print(f'Qualified page name {" "*(maxlen-20)} | Updated | Updated diagrams')
                print(f'--------------------{"-"*(maxlen-20)} | ------- | ----------------')
                for qualname, stats in self._summary.items():
                    print(f'{qualname:{maxlen}s} |    {"y" if stats["updated"] else "n"}    | {stats["updated_attachments"]}')

                if self._errors:
                    print()
                    print('Errors:')
                    print(f'Qualified page name {" "*(maxlen-20)} | Error')
                    print(f'--------------------{"-"*(maxlen-20)} | -------------------------------------')
                    for qualname, errors in self._errors:
                        print(f'{qualname:{maxlen}s} | {errors}')
            else:
                print('No changes')

    def _process_root_page(self, cfl_root_pageid, rootpage):
        logger.info(f'Rootpage cfl_id={cfl_root_pageid}')
        self._summary[rootpage.pagedata.qualifiedName] = {
            'updated': False,
            'updated_attachments': 0,
            'errors': [],
        }
        self._update_page_contents(cfl_root_pageid, rootpage.pagedata, is_root=True)

        cfl_children = self._cfl.get_children(cfl_root_pageid)

        if self._delete_children and cfl_children['results']:
            results = cfl_children['results']
            bar = IncrementalBar(f'Deleting {len(results)} children',
                                               max=len(results),
                                               suffix='%(percent)d%%')

            for child in results:
                self._cfl.delete_page(child['id'])
                bar.next()

            bar.finish()

            cfl_children = self._cfl.get_children(cfl_root_pageid)

        for subpage in rootpage.subpages:
            pagedata = subpage.pagedata

            self._summary[pagedata.qualifiedName] = {
                'updated': False,
                'updated_attachments': 0,
                'errors': [],
            }

            cfl_id = self._find_page_by_elid(cfl_children, pagedata.elementid)

            if not cfl_id:
                try:
                    newpage = self._cfl.create_page(cfl_root_pageid, pagedata.name, 'Initial import')
                except APIError as e:
                    logger.info(f'Cannot create page qualname={pagedata.qualifiedName} error={e}')
                    self._errors.append((pagedata.qualifiedName, e))
                    return

                cfl_id = newpage['id']
                logger.info(f'  Created new page id={cfl_id}')
                self._cfl.set_property(cfl_id, 'md_elid', pagedata.elementid)

            self._update_page_contents(cfl_id, pagedata)

    def _update_page_contents(self, cfl_id, pagedata, is_root=False):
        if self._print_summary:
            self._current_bar = IncrementalBar(f'Processing {pagedata.qualifiedName:64s}',
                                               max=self._total_steps(pagedata),
                                               suffix='%(percent)d%%')

        page_hash = utils.generate_hash(pagedata)
        body = self._renderer.render_page(pagedata=pagedata,
                                          hash=page_hash,
                                          version_info=self._version_info)

        logger.info(f'Processing page: qualname={pagedata.qualifiedName} '
                    f'elid={pagedata.elementid} '
                    f'bodylen={len(body)}')

        self._barnext()

        if self._force_updates or not utils.test_hash(self._cfl.get_page_body(cfl_id), page_hash):
            try:
                response = self._cfl.update_page(cfl_id, pagedata.name, body)
            except APIError as e:
                logger.info(f'Cannot update page qualname={pagedata.qualifiedName} error={e}')
                self._errors.append((pagedata.qualifiedName, e))
                return

            logger.info(f'  Updated page content to version={response["version"]["number"]}')
            self._summary[pagedata.qualifiedName]['updated'] = True
        else:
            logger.info('  Page requires no update')

        self._barnext()
        self._upload_attachments(cfl_id, pagedata)
        self._barnext()
        self._set_labels(cfl_id, pagedata, is_root)
        self._barnext()

        if not self._skip_restrictions:
            self._cfl.set_page_restrictions(cfl_id)
            logger.info(f'  Restrictions applied')

        if self._print_summary:
            # Not sure why finish() doesn't complete the bar
            while self._current_bar.remaining > 0:
                self._current_bar.next()
            self._current_bar.finish()

    def _upload_attachments(self, cfl_id, pagedata):
        todo = []
        page_attachments = self._cfl.get_attachments(cfl_id)
        for diagram in pagedata.diagrams:
            filename = os.path.basename(diagram.image)
            if self._force_updates or filename not in page_attachments:
                logger.info(f'  Adding diagram {filename} to the todo since it is missing')
                todo.append(diagram.image)
            else:
                lm_attached = dateutil.parser.parse(page_attachments[filename]['last_updated'])
                lm_available = diagram.lastModifiedDate

                if diagram.type == 'table':
                    logger.info(f'  Adding diagram {filename} to the todo since it is a table')
                    todo.append(diagram.image)
                elif not isinstance(lm_available, datetime.datetime) or lm_available > lm_attached:
                    logger.info(f'  Adding diagram {filename} to the todo due to time comparison: '
                                f'lm_available={lm_available} lm_attached={lm_attached}')
                    todo.append(diagram.image)

        if len(todo) == 0:
            logger.info('  Diagrams require no update')
        else:
            logger.info(f'  Uploading attachments (count={len(todo)})')

            for attachment in todo:
                if self._print_summary:
                    self._current_bar.next()

                logger.info(f'    - {attachment}')
                self._cfl.upload_attachment(cfl_id, attachment)

            self._summary[pagedata.qualifiedName]['updated_attachments'] = len(todo)

    def _total_steps(self, pagedata):
        return len(pagedata.diagrams) + 4

    def _barnext(self):
        if self._print_summary:
            self._current_bar.next()

    def _set_labels(self, cfl_id, subpage, is_root):
        labels = ['_model'] + [f'_{st.lower()}' for st in subpage.stereotypes]

        if is_root:
            labels += ['_model_root']

        logger.info(f'  Setting labels: {labels}')
        self._cfl.set_labels(cfl_id, labels)

    def _find_page_by_elid(self, cfl_children, elid):
        for cfl_child in cfl_children['results']:
            prop = self._cfl.get_property(cfl_child['id'], 'md_elid')

            if prop and prop['value'] == elid:
                return cfl_child['id']

        return None
