# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information

    Kodi service entry: owns the localhost MoQ/WebSocket proxy for the
    whole session. The server is bound here, in this invoker, at login;
    resolvers running in the plugin router invoker only reuse the port.
    On abort everything is torn down before this script ends, so no
    Python thread outlives us and Kodi can exit cleanly.
'''

import os
import sys

_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from moq_proxy import run_service  # noqa: E402

if __name__ == '__main__':
    run_service()
