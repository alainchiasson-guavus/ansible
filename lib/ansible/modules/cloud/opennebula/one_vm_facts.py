#!/usr/bin/python
# -*- coding: utf-8 -*-

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

"""
(c) 2018, Milan Ilic <milani@nordeus.com>
(c) 2018, Alain Chiasson <alain@chiasson.org>

This file is part of Ansible

Ansible is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Ansible is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a clone of the GNU General Public License
along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
"""

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'metadata_version': '1.1'}

DOCUMENTATION = '''
---
module: one_vm_facts
short_description: Gather facts about OpenNebula virtaul machines
description:
  - Gather facts about OpenNebula virtaul machines
version_added: "2.6"
requirements:
  - python-oca
options:
  api_url:
    description:
      - URL of the OpenNebula RPC server.
      - It is recommended to use HTTPS so that the username/password are not
      - transferred over the network unencrypted.
      - If not set then the value of the C(ONE_URL) environment variable is used.
  api_username:
    description:
      - Name of the user to login into the OpenNebula RPC server. If not set
      - then the value of the C(ONE_USERNAME) environment variable is used.
  api_password:
    description:
      - Password of the user to login into OpenNebula RPC server. If not set
      - then the value of the C(ONE_PASSWORD) environment variable is used.
  ids:
    description:
      - A list of VM ids whose facts you want to gather.
    aliases: ['id']
  name:
    description:
      - A C(name) of the vms whose facts will be gathered.
      - If the C(name) begins with '~' the C(name) will be used as regex pattern
      - which restricts the list of vms (whose facts will be returned) whose names match specified regex.
      - Also, if the C(name) begins with '~*' case-insensitive matching will be performed.
      - See examples for more details.
author:
    - "Milan Ilic (@ilicmilan)"
    - "Alain Chiasson (@alainchiasson)"
'''

EXAMPLES = '''
# Gather facts about all vms
- one_vm_facts:
  register: result

# Print all vmss facts
- debug:
    msg: result

# Gather facts about an vms using ID
- one_vm_facts:
    ids:
      - 123

# Gather facts about an vms using the name
- one_vm_facts:
    name: 'foo-vms'
  register: foo_vms

# Gather facts about all vmss whose name matches regex 'app-vms-.*'
- one_vm_facts:
    name: '~app-vm-.*'
  register: app_vms

# Gather facts about all vmss whose name matches regex 'foo-vms-.*' ignoring cases
- one_vm_facts:
    name: '~*foo-vm-.*'
  register: foo_vms
'''

RETURN = '''
vms:
    description: A list of vms info
    type: complex
    returned: success
    contains:
        id:
            description: vms id
            type: int
            sample: 153
        name:
            description: vms name
            type: string
            sample: app1
        group_id:
            description: vms's group id
            type: int
            sample: 1
        group_name:
            description: vms's group name
            type: string
            sample: one-users
        owner_id:
            description: vms's owner id
            type: int
            sample: 143
        owner_name:
            description: vms's owner name
            type: string
            sample: ansible-test
        state:
            description: state of vms instance
            type: string
            sample: READY

        memory:
            description:
              - The size of the memory for new instances (in MB, GB, ...)
        disk_size:
            description:
              - The size of the disk created for new instances (in MB, GB, TB,...).
              - NOTE':' This option can be used only if the VM template specified with
              - C(template_id)/C(template_name) has exactly one disk.
        cpu:
            description:
              - Percentage of CPU divided by 100 required for the new instance. Half a
              - processor is written 0.5.
        vcpu:
            description:
              - Number of CPUs (cores) new VM will have.
        networks:
            description:
              - A list of dictionaries with network parameters. See examples for more details.
            default: []
        mode:
            description:
              - Set permission mode of the instance in octet format, e.g. C(600) to give owner C(use) and C(manage) and nothing to group and others.
        labels:
            description:
              - A list of labels to associate with new instances, or for setting
              - C(state) of instances with these labels.
            default: []
        attributes:
            description:
              - A dictionary of key/value attributes to add to new instances, or for
              - setting C(state) of instances with these attributes.
              - Keys are case insensitive and OpenNebula automatically converts them to upper case.
              - Be aware C(NAME) is a special attribute which sets the name of the VM when it's deployed.
              - C(#) character(s) can be appended to the C(NAME) and the module will automatically add
              - indexes to the names of VMs.
              - For example':' C(NAME':' foo-###) would create VMs with names C(foo-000), C(foo-001),...
              - When used with C(count_attributes) and C(exact_count) the module will
              - match the base name without the index part.
            default: {}
        lcm_state:
            description:
              - The Life cycle state of an Active VM
              - See `Virtual Machine State reference <http://docs.opennebula.org/5.6/operation/references/vm_states.html#vm-states>`
            default: string
        uptime_h:
            description:
                - uptime in hours. Rounded.


'''

try:
    import oca
    HAS_OCA = True
except ImportError:
    HAS_OCA = False

from ansible.module_utils.basic import AnsibleModule
import os


def get_all_vms(client):
    pool = oca.VirtualMachinePool(client)
    # Filter -2 means fetch all vm user can Use
    pool.info(filter=-2)

    return pool

VM_STATES = ['INIT', 'PENDING', 'HOLD', 'ACTIVE', 'STOPPED', 'SUSPENDED', 'DONE', 'FAILED', 'POWEROFF', 'UNDEPLOYED']

LCM_STATES = ['LCM_INIT', 'PROLOG', 'BOOT', 'RUNNING', 'MIGRATE', 'SAVE_STOP',
              'SAVE_SUSPEND', 'SAVE_MIGRATE', 'PROLOG_MIGRATE', 'PROLOG_RESUME',
              'EPILOG_STOP', 'EPILOG', 'SHUTDOWN', 'STATE13', 'STATE14', 'CLEANUP_RESUBMIT', 'UNKNOWN', 'HOTPLUG', 'SHUTDOWN_POWEROFF',
              'BOOT_UNKNOWN', 'BOOT_POWEROFF', 'BOOT_SUSPENDED', 'BOOT_STOPPED', 'CLEANUP_DELETE', 'HOTPLUG_SNAPSHOT', 'HOTPLUG_NIC',
              'HOTPLUG_SAVEAS', 'HOTPLUG_SAVEAS_POWEROFF', 'HOTPULG_SAVEAS_SUSPENDED', 'SHUTDOWN_UNDEPLOY']


def get_vm_info(client, vm):
    vm.info()

    networks_info = []

    disk_size = ''
    if hasattr(vm.template, 'disks'):
        disk_size = vm.template.disks[0].size + ' MB'

    if hasattr(vm.template, 'nics'):
        for nic in vm.template.nics:
            networks_info.append({'ip': nic.ip, 'mac': nic.mac, 'name': nic.network, 'security_groups': nic.security_groups})

    import time

    current_time = time.localtime()
    vm_start_time = time.localtime(vm.stime)

    vm_uptime = time.mktime(current_time) - time.mktime(vm_start_time)
    vm_uptime /= (60 * 60)

    permissions_str = parse_vm_permissions(client, vm)

    # LCM_STATE is VM's sub-state that is relevant only when STATE is ACTIVE
    vm_lcm_state = None
    if vm.state == VM_STATES.index('ACTIVE'):
        vm_lcm_state = LCM_STATES[vm.lcm_state]

    vm_labels, vm_attributes = get_vm_labels_and_attributes_dict(client, vm.id)

    info = {
        'id': vm.id,
        'name': vm.name,
        'state': VM_STATES[vm.state],
        'lcm_state': vm_lcm_state,
        'owner_name': vm.uname,
        'owner_id': vm.uid,
        'networks': networks_info,
        'disk_size': disk_size,
        'memory': vm.template.memory + ' MB',
        'vcpu': vm.template.vcpu,
        'cpu': vm.template.cpu,
        'group_name': vm.gname,
        'group_id': vm.gid,
        'uptime_h': int(vm_uptime),
        'attributes': vm_attributes,
        'mode': permissions_str,
        'labels': vm_labels
    }

    return info


def parse_vm_permissions(client, vm):

    import xml.etree.ElementTree as ET
    vm_XML = client.call('vm.info', vm.id)
    root = ET.fromstring(vm_XML)

    perm_dict = {}

    root = root.find('PERMISSIONS')

    for child in root:
        perm_dict[child.tag] = child.text

    '''
    This is the structure of the 'PERMISSIONS' dictionary:
   "PERMISSIONS": {
                      "OWNER_U": "1",
                      "OWNER_M": "1",
                      "OWNER_A": "0",
                      "GROUP_U": "0",
                      "GROUP_M": "0",
                      "GROUP_A": "0",
                      "OTHER_U": "0",
                      "OTHER_M": "0",
                      "OTHER_A": "0"
                    }
    '''

    owner_octal = int(perm_dict["OWNER_U"]) * 4 + int(perm_dict["OWNER_M"]) * 2 + int(perm_dict["OWNER_A"])
    group_octal = int(perm_dict["GROUP_U"]) * 4 + int(perm_dict["GROUP_M"]) * 2 + int(perm_dict["GROUP_A"])
    other_octal = int(perm_dict["OTHER_U"]) * 4 + int(perm_dict["OTHER_M"]) * 2 + int(perm_dict["OTHER_A"])

    permissions = str(owner_octal) + str(group_octal) + str(other_octal)

    return permissions


def get_vms_by_ids(module, client, ids):
    vms = []
    pool = get_all_vms(client)

    for vm in pool:
        if str(vm.id) in ids:
            vms.append(vm)
            ids.remove(str(vm.id))
            if len(ids) == 0:
                break

    if len(ids) > 0:
        module.fail_json(msg='There is no VM(s) with id(s)=' + ', '.join('{id}'.format(id=str(vm_id)) for vm_id in ids))

    return vms


def get_vms_by_name(module, client, name_pattern):

    vms= []
    pattern = None

    pool = get_all_vms(client)

    if name_pattern.startswith('~'):
        import re
        if name_pattern[1] == '*':
            pattern = re.compile(name_pattern[2:], re.IGNORECASE)
        else:
            pattern = re.compile(name_pattern[1:])

    for vm in pool:
        if pattern is not None:
            if pattern.match(vm.name):
                vms.append(vm)
        elif name_pattern == vm.name:
            vms.append(vm)
            break

    # if the specific name is indicated
    if pattern is None and len(vms) == 0:
        module.fail_json(msg="There is no VM with name=" + name_pattern)

    return vms

def get_vm_labels_and_attributes_dict(client, vm_id):
    import xml.etree.ElementTree as ET
    vm_XML = client.call('vm.info', vm_id)
    root = ET.fromstring(vm_XML)

    attrs_dict = {}
    labels_list = []

    root = root.find('USER_TEMPLATE')

    for child in root:
        if child.tag != 'LABELS':
            attrs_dict[child.tag] = child.text
        else:
            if child.text is not None:
                labels_list = child.text.split(',')

    return labels_list, attrs_dict


def get_connection_info(module):

    url = module.params.get('api_url')
    username = module.params.get('api_username')
    password = module.params.get('api_password')

    if not url:
        url = os.environ.get('ONE_URL')

    if not username:
        username = os.environ.get('ONE_USERNAME')

    if not password:
        password = os.environ.get('ONE_PASSWORD')

    if not(url and username and password):
        module.fail_json(msg="One or more connection parameters (api_url, api_username, api_password) were not specified")
    from collections import namedtuple

    auth_params = namedtuple('auth', ('url', 'username', 'password'))

    return auth_params(url=url, username=username, password=password)


def main():
    fields = {
        "api_url": {"required": False, "type": "str"},
        "api_username": {"required": False, "type": "str"},
        "api_password": {"required": False, "type": "str", "no_log": True},
        "ids": {"required": False, "aliases": ['id'], "type": "list"},
        "name": {"required": False, "type": "str"},
    }

    module = AnsibleModule(argument_spec=fields,
                           mutually_exclusive=[['ids', 'name']],
                           supports_check_mode=True)

    if not HAS_OCA:
        module.fail_json(msg='This module requires python-oca to work!')

    auth = get_connection_info(module)
    params = module.params
    ids = params.get('ids')
    name = params.get('name')
    client = oca.Client(auth.username + ':' + auth.password, auth.url)

    result = {'vms': []}
    vmss = []

    if ids:
        vms = get_vms_by_ids(module, client, ids)
    elif name:
        vms = get_vms_by_name(module, client, name)
    else:
        vms = get_all_vms(client)

    for vm in vms:
        result['vms'].append(get_vm_info(client, vm))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
