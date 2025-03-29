# -*- coding: utf-8 -*-

import six

import simplejson as json


def byteify(data, ignore_dicts=False):
    if isinstance(data, six.string_types):
        if six.PY2:
            return data.encode('utf-8')
        else:
            return data
    if isinstance(data, list):
        return [byteify(item, ignore_dicts=True) for item in data]
    if isinstance(data, dict) and not ignore_dicts:
        return dict([(byteify(key, ignore_dicts=True), byteify(value, ignore_dicts=True)) for key, value in six.iteritems(data)])
    return data


def json_loads_as_str(json_text):
    return byteify(json.loads(json_text, object_hook=byteify), ignore_dicts=True)


