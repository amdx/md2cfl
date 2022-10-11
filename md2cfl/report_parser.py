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
from pathlib import Path
import html

from lxml import etree

import dateutil.parser
from dateutil import tz

DIAGRAM_TYPES_MAP = {
    'Generic Table': 'table',
    'SysML Block Definition Diagram': 'bdd',
    'SysML Internal Block Diagram': 'ibd',
    'SysML Activity Diagram': 'act',
    'SysML Parametric Diagram': 'par',
    'SysML Package Diagram': 'pkg',
    'Requirement Diagram': 'req',
    'SysML Use Case Diagram': 'uc',
}


logger = logging.getLogger(__name__)


def date_parser(text):
    try:
        dt = dateutil.parser.parse(text).replace(tzinfo=tz.tzlocal())
        return dt
    except dateutil.parser.ParserError:
        return 'N/A'


def diagram_type_xformer(text):
    if text in DIAGRAM_TYPES_MAP:
        return DIAGRAM_TYPES_MAP[text]
    else:
        return text


def cast_documentation(node):
    html_attrib = node.attrib.get('html')
    if html_attrib:
        is_html = html_attrib.lower() == 'true'
    else:
        is_html = False

    if is_html or node.text is None:
        return node.text
    else:
        return html.escape(node.text)


class BaseRep:
    XFORMERS = {}
    HASH_ATTRIBUTES = []

    def __init__(self, xmlnode):
        for node in xmlnode:
            if node.tag in self.XFORMERS:
                data = self.XFORMERS[node.tag](node)
            else:
                data = node.text

            setattr(self, node.tag, data)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.__dict__}>'

    def __mdrepr__(self):
        return str(self).encode()


class Diagram(BaseRep):
    REPORT_BASEPATH = Path('.')
    XFORMERS = {
        'lastModifiedDate': lambda node: date_parser(node.text),
        'lastModifiedBy': lambda node: node.text.strip(),
        'creationDate': lambda node: date_parser(node.text),
        'image': lambda node: Diagram.REPORT_BASEPATH / node.text.strip(),
        'type': lambda node: diagram_type_xformer(node.text),
        'documentation': cast_documentation,
    }

    def __mdrepr__(self):
        return (self.lastModifiedDate + self.image).encode()


class PageData(BaseRep):
    HASH_ATTRIBUTES = ['stereotypes', 'name', 'qualifiedName', 'elementid',
                       'documentation', 'diagrams']

    XFORMERS = {
        'stereotypes': lambda node: [child.text for child in node],
        'diagrams': lambda node: [Diagram(diagram) for diagram in node.iter('diagram')],
        'documentation': cast_documentation,
    }


class Subpage(PageData):
    XFORMERS = {
        'pagedata': lambda node: PageData(node),
    }


class RootPage(BaseRep):
    XFORMERS = {
        'subpages': lambda node: [Subpage(subpage) for subpage in node.iter('subpage')],
        'pagedata': lambda node: PageData(node),
    }


class VersionInfo:
    def __init__(self, version, stepping):
        self.version = version
        self.stepping = stepping

    def __repr__(self):
        return f'<{self.__class__.__name__} schema version={self.version} stepping={self.stepping}>'


def parse(report):
    Diagram.REPORT_BASEPATH = Path(report).absolute().parent
    schema_file = str(Path(Path(__file__).absolute().parent, 'data/report.xsd'))

    try:
        tree = etree.parse(report)
    except etree.XMLSyntaxError as e:
        logger.error(f'The report {report} failed XML syntax validation: {e}')

    xsd = etree.XMLSchema(etree.parse(schema_file))

    if not xsd.validate(tree):
        logger.error(f'The report {report} failed schema validation:')

        for error in xsd.error_log:
            logger.error(f'  {error}')
            return None, None

    root = tree.getroot()

    if root.tag != 'report':
        raise RuntimeError('Incompatible report format')

    version = int(root.attrib['version'])
    stepping = int(root.attrib['stepping'])

    report = {}

    for rootpage_node in root.iter('rootpage'):
        cfl_pageid = int(rootpage_node.find('pageid').text)

        rootpage = RootPage(rootpage_node)
        report[cfl_pageid] = rootpage

    return VersionInfo(version, stepping), report


if __name__ == '__main__':
    vi, rep = parse('samples/output.xml')

    if rep:
        for cfid, node in rep.items():
            print(node.pagedata)
