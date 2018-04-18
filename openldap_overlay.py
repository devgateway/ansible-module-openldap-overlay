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
    import ldap.filter

    HAS_LDAP = True
except ImportError:
    HAS_LDAP = False

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

class OpenldapOverlay(object):
    ATTR_OVERLAY = 'olcOverlay'

    def __init__(self, module):
        self._module = module
        self._connection = self._connect()

        # find database DN
        database_dn = self._get_database_dn(module.params['suffix'])

        self._dn, self._old_attrs = self._find_overlay(database_dn)

    def _connect(self):
        """Connect to slapd thru a socket using EXTERNAL auth."""

        # Slapd can only be managed over a local socket
        connection = ldap.initialize('ldapi:///')
        try:
            # bind as Ansible user (default: root)
            connection.sasl_interactive_bind_s('', ldap.sasl.external())
        except ldap.LDAPError as e:
            self._module.fail_json(
                msg = 'Can\'t bind to local socket',
                details = to_native(e),
                exception = traceback.format_exc()
            )

        return connection

    def _get_database_dn(self, suffix):
        """Find the DB DN in LDAP."""

        filterstr = '(olcSuffix={})'.format(
            ldap.filter.escape_filter_chars(suffix)
        )
        search_results = self._connection.search_s(
            base = 'cn=config',
            scope = ldap.SCOPE_ONELEVEL,
            filterstr = filterstr,
            attrlist = ['dn']
        )

        if search_results:
            dn = search_results[0][0]
        else:
            raise RuntimeError('Database {} not found'.format(suffix))

        return dn

    def _find_overlay(self, database_dn):
        search_results = self._connection.search_s(
            base = database_dn,
            scope = ldap.SCOPE_ONELEVEL,
            filterstr = self.__class__.ATTR_OVERLAY
        )

        if search_results:
            result = search_results[0]
        else:
            result = (None, {})

        return result

    def ensure_absent(self):
        overlay_exists = bool(self._dn)

        if not self._module.check_mode and overlay_exists:
            self._connection.delete_s(self._dn)

        return overlay_exists

def main():
    module = AnsibleModule(
        argument_spec = {
            'config': dict(default = {}, type = 'dict'),
            'object_class': dict(required = True),
            'overlay': dict(required = True),
            'state': dict(default = 'present', choices = ['present', 'absent']),
            'suffix': dict(required = True)
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
