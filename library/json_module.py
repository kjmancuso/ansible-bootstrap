#!/usr/bin/python

from ansible.module_utils.basic import *

import json

try:
    import commentjson

    json_load = commentjson.load
except ImportError:
    json_load = json.load

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: json_module
short_description: Manipulate json file
'''

EXAMPLES = '''

'''

RETURN = '''

'''


class Ref(object):

    def __init__(self, ref, key):
        self.ref = ref
        self.key = key

    @property
    def value(self):
        return self.ref[self.key]

    @value.setter
    def value(self, data):
        self.ref[self.key] = data

    def delete(self):
        del self.ref[self.key]

    def exists(self):
        return self.key in self.ref


def type_coerce(target):
    if not isinstance(target, basestring):
        return target

    if target.isdigit():
        return int(target)
    if target == 'null':
        return None
    if target == 'false':
        return False
    if target == 'true':
        return True
    if '[' in target and ']' in target:
        arr = []
        target = target.replace('[', '').replace(']', '').split(',')
        for e in target:
            arr.append(e.replace('"', '').lstrip())
        target = arr
    return target


def query(json_data, path):
    parts = re.split(r'(?<!\\)', path)

    ref = json_data
    for part in parts[:-1]:
        if part not in ref:
            ref[part] = {}
        ref = ref[part]

    last_part = parts[-1]
    return Ref(ref, last_part)


def extend_action(json_data, change):
    # validate
    result = query(json_data, change['path'])
    new_list = [type_coerce(v) for v in change['values']
                if type_coerce(v) not in result.value]
    if new_list:
        result.value.extend(new_list)
        return True


def set_action(json_data, change):
    # validate
    result = query(json_data, change['path'])
    value = type_coerce(change['value'])
    if not result.exists():
        result.value = value
        return True

    if result.value != value:
        result.value = value
        return True


def append_action(json_data, change):
    # validate
    result = query(json_data, change['path'])
    value = type_coerce(change['value'])
    if not result.exists():
        result.value = [value]
        return True

    if value not in result.value:
        result.value.append(value)
        return True


def unset_action(json_data, change):
    # validate
    result = query(json_data, change['path'])
    if result.exists():
        result.delete()
        return True


CHANGES_MAP = {
    "set": set_action,
    "unset": unset_action,
    "extend": extend_action,
    "append": append_action
}


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def main():
    changed = False

    module_args = {
        "path": {"type": 'path', "required": True},
        "changes": {"type": 'list', "required": True}
    }

    module = AnsibleModule(argument_spec=module_args)
    path = os.path.expanduser(module.params['path'])
    mkdir_p(os.path.dirname(path))
    if os.path.exists(path):
        with open(path) as f:
            json_data = json_load(f)
    else:
        json_data = {}

    for change in module.params['changes']:
        if CHANGES_MAP.get(change['type'])(json_data, change):
            changed = True

    if changed:
        with open(path, 'w') as f:
            json.dump(json_data, f, indent=2, separators=(',', ': '), sort_keys=True)

    results = dict()
    results['changed'] = changed

    module.exit_json(**results)


if __name__ == '__main__':
    main()

