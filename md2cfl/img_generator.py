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

from PIL import Image, ImageDraw


def generate_picture(filepath, index, caption='IMG'):
    image = Image.new('RGB', (200, 150), color='black')
    draw = ImageDraw.Draw(image)
    draw.text((100, 75), f'{caption} {index}', fill='white', align='center')
    image.save(filepath)
