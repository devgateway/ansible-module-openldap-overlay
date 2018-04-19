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
short_description: Configure overlays in OpenLDAP
description:
  - This module creates and configures overlays in OpenLDAP.
  - Deleting overlays is not supported as of OpenLDAP 2.4, but might appear in 2.5.
  - Standard and custom overlays are supported as long as they use dynamic configuration.
  - Check mode is supported.
version_added: null
author: Development Gateway (@devgateway)
options:
  config:
    description:
      - Dictionary of overlay configuration options, e.g. C(olcMemberOfRefInt).
      - Keys must be valid attribute names, typically starting with "olc".
      - Values must be either scalars (to be converted to strings), or lists of strings.
  object_class:
    description:
      - Object class of the overlay dynamic configuration, e.g. C(olcMemberOf).
  overlay:
    description:
      - Overlay name as in C(olcOverlay) attribute.
  state:
    description:
      - Use C(present) to create or update the overlay, or C(absent) to delete.
      - Delete operation is not supported by OpenLDAP as of v2.4.
    default: present
    choices: [absent, present]
  suffix:
    description:
      - Database suffix, e.g. C(dc=example,dc=org).
    required: true
notes: null
requirements:
  - python-ldap
'''

EXAMPLES = '''
---
- hosts: ldap-servers
  tasks:
    - name: Configure overlay
      openldap_overlay:
        suffix: dc=example,dc=org
        overlay: memberof
        object_class: olcMemberOf
        config:
          olcMemberOfDangling: ignore
          olcMemberOfRefInt: true
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
        self._database = self._get_database_dn(module.params['suffix'])

        self._dn, self._old_attrs = self._find_overlay()
        self._attrs = self._get_attributes()
        # if overlay found, keep its numbered RDN, e.g. olcOverlay={1}ppolicy
        overlay = self.__class__.ATTR_OVERLAY
        try:
          self._attrs[overlay] = self._old_attrs[overlay]
        except KeyError:
          pass

    def _get_attributes(self):
        attrs = {}
        for name, value in self._module.params['config'].iteritems():
            type_ = type(value)
            if type_ is bool:
                value = ['TRUE'] if value else ['FALSE']
            elif type_ is not list:
                value = [value]
            attrs[name] = value

        attrs['objectClass'] = [self._module.params['object_class']]

        return attrs

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

    def _find_overlay(self):
        filterstr = '({}={})'.format(
            self.__class__.ATTR_OVERLAY,
            self._module.params['overlay']
        )

        search_results = self._connection.search_s(
            base = self._database,
            scope = ldap.SCOPE_ONELEVEL,
            filterstr = filterstr
        )

        if search_results:
            result = search_results[0]
        else:
            result = (None, {})

        return result

    def ensure_present(self):
        if self._dn:
            ldap_function = self._connection.modify_s
            dn = self._dn
            modlist = ldap.modlist.modifyModlist(self._old_attrs, self._attrs)
            # if any changes prepared
            changed = bool(modlist)
        else:
            ldap_function = self._connection.add_s
            dn = '{}={},{}'.format(
                self.__class__.ATTR_OVERLAY,
                self._module.params['overlay'],
                self._database
            )
            modlist = ldap.modlist.addModlist(self._attrs)
            # creating will always change things
            changed = True

        if not self._module.check_mode:
            ldap_function(dn, modlist)

        return changed

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
