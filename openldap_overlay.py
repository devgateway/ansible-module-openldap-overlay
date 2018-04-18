#!/usr/bin/python

# Copyright 2018, Development Gateway <info@developmentgateway.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Uses portions of ldap_entry.py by Peter Sagerson and Jiri Tyr, GPL v3

from __future__ import absolute_import
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: openldap_overlay
short_description: 
description:
version_added: null
author: Development Gateway (@devgateway)
options:
notes:
requirements:
  - python-ldap
'''

EXAMPLES = '''
'''

try:
    import ldap
    import ldap.modlist
    import ldap.sasl

    HAS_LDAP = True
except ImportError:
    HAS_LDAP = False

import traceback, os, stat, subprocess

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

def main():
    module = AnsibleModule(
        argument_spec = {
            'config': dict(default = {}, type = 'dict'),
            'overlay': dict(required = True, choices = []), # TODO
            'state': dict(default = 'present', choices = ['present', 'absent'])
        },
        supports_check_mode = True
    )

    # check if imports succeeded
    if not HAS_LDAP:
        module.fail_json(msg = 'Missing required "ldap" module (install python-ldap package)')

    try:
        overlay = OpenldapOverlay(module)

        if module.params['state'] == 'absent':
            changed = overlay.ensure_absent()
        else:
            changed = overlay.ensure_present()
    except Exception as e:
        module.fail_json(
            msg = 'Overlay configuration failed',
            details = to_native(e),
            exception = traceback.format_exc()
        )

    module.exit_json(changed = changed)

if __name__ == '__main__':
    main()
