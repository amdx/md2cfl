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
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


class Renderer:
    def __init__(self):
        templates_dir = Path(Path(__file__).absolute().parent, 'data/cfl_templates')

        file_loader = FileSystemLoader(templates_dir)
        self._env = Environment(loader=file_loader)

        # Custom filters
        self._env.filters['basename'] = lambda path: Path(path).name

    def render_page(self, pagedata, version_info, hash):
        template = self._env.get_template('cfl_page.html')

        return template.render(pagedata=pagedata,
                               version_info=version_info,
                               hash=hash,
                               now=datetime.datetime.now())
