# `openldap_overlay` module for Ansible

Configure overlays in OpenLDAP

## Description

This module creates and configures overlays in OpenLDAP. Deleting overlays is not supported as of
OpenLDAP 2.4, but might appear in 2.5. Standard and custom overlays are supported as long as they
use dynamic configuration. Check mode is supported.

## Options

### `config`

Dictionary of overlay configuration options, e.g. `olcMemberOfRefInt`. Keys must be valid attribute
names, typically starting with `olc`. Values must be either scalars (to be converted to strings),
or lists of strings.

### `object_class`

Object class of the overlay dynamic configuration, e.g. `olcMemberOf`.

### `overlay`

Overlay name as in `olcOverlay` attribute.

### `state`

Use `present` to create or update the overlay, or `absent` to delete. Delete operation is not
supported by OpenLDAP as of v2.4.

Choices:

- `absent`
- `present`

### `suffix`

Database suffix, e.g. `dc=example,dc=org`.

## Requirements

python-ldap

## Copyright

2018, Development Gateway (@devgateway), GPL v3+
