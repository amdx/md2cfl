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
import pathlib
import json
import logging
import platform

logger = logging.getLogger(__name__)


class Prefs:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        prefs_file = self._determine_prefs_file()

        logger.debug(f'Prefs file: {prefs_file}')
        if prefs_file.exists():
            try:
                self.data = json.load(open(prefs_file))
            except ValueError:
                logger.warning(f'Prefs file {prefs_file} is corrupted')
                return False

            logger.debug(f'Prefs file contents: {self.data}')
            return True
        else:
            return False

    def save(self):
        prefs_file = self._determine_prefs_file()

        json.dump(self.data, open(prefs_file, 'w'))

    def _determine_prefs_file(self):
        system = platform.system()
        if system in ('Darwin', 'Linux'):
            prefs_file = pathlib.Path.home() / '.mdimporterrc'
        elif system == 'Windows':
            prefs_file = pathlib.Path(
                os.getenv('LOCALAPPDATA')) / 'md2cfl.rc'
        else:
            raise RuntimeError(f'Unknown system {system}')
        return prefs_file


if __name__ == '__main__':
    pass
