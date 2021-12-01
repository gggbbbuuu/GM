# -*- coding: utf-8 -*-

import ast
import json
import xbmcvfs

def read_properties(PROPERTIES_FILE):
    payload = []
    if xbmcvfs.exists(PROPERTIES_FILE):
        with xbmcvfs.File(PROPERTIES_FILE, 'r') as propcontent:
            raw_properties = propcontent.read()
        try:
            payload = json.loads(raw_properties)
        except json.decoder.JSONDecodeError:
            payload = ast.literal_eval(raw_properties)
        except:
            payload = []

    return payload


def write_properties(data, PROPERTIES_FILE):
    payload = json.dumps(data, indent=4)
    with xbmcvfs.File(PROPERTIES_FILE, 'w') as f:
        f.write(payload)

