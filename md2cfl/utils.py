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
import hashlib
import re

logger = logging.getLogger(__name__)


def generate_hash(pagedata):
    hash = hashlib.sha256()
    for attrname in pagedata.HASH_ATTRIBUTES:
        attr = getattr(pagedata, attrname)

        if attr is None:
            continue
        elif hasattr(attr, '__mdhash__'):
            hash.update(attr.__mdrepr__())
        elif isinstance(attr, str):
            hash.update(attr.encode())
        elif isinstance(attr, list):
            hash.update(str(attr).encode())
        else:
            raise RuntimeError(f'Pagedata attribute {attrname} (type={type(attr)}) '
                               f'does not support hashing')

    return hash.hexdigest()


def extract_hash(body):
    match = re.search(r'\$hash=(\w{64})', body)
    if match:
        return match.group(1)
    else:
        return None


def test_hash(body, hash):
    hash_text = extract_hash(body)
    return hash_text == hash
