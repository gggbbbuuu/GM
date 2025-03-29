# -*- coding: utf-8 -*-

"""
    Zouzounia TV Addon
    Author: Twilight0

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from tulip.url_dispatcher import urldispatcher
from tulip.cache import FunctionCache
from tulip.control import openSettings


@urldispatcher.register('cache_clear')
def cache_clear():

    FunctionCache().reset_cache(notify=True, label_success=30010)


@urldispatcher.register('settings')
def settings():

    openSettings()
