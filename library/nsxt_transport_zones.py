#!/usr/bin/env python
#
# Copyright 2018 VMware, Inc.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''TODO
author: Rahul Raghuvanshi
'''

EXAMPLES = '''
- name: Create transport zone
  nsxt_transport_zones:
    hostname: "10.192.167.137"
    username: "admin"
    password: "Admin!23Admin"
    validate_certs: False
    resource_type: "TransportZone"
    display_name: "TZ1"
    description: "NSX configured Test Transport Zone"
    transport_type: "OVERLAY"
    host_switch_name: "hostswitch4"
    #zone_id: "21ff0e36-1624-4c18-be2f-070513079185"
    state: "present"
'''

RETURN = '''# '''

import json, time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.vmware import vmware_argument_spec, request
from ansible.module_utils._text import to_native

def get_transport_zone_params(args=None):
    args_to_remove = ['state', 'username', 'password', 'port', 'hostname', 'validate_certs']
    for key in args_to_remove:
        args.pop(key, None)
    for key, value in args.copy().items():
        if value == None:
            args.pop(key, None)
    return args

def get_transport_zones(module, manager_url, mgr_username, mgr_password, validate_certs):
    try:
      (rc, resp) = request(manager_url+ '/transport-zones', headers=dict(Accept='application/json'),
                      url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
    except Exception as err:
      module.fail_json(msg='Error accessing transport zones. Error [%s]' % (to_native(err)))
    return resp

def get_tz_from_display_name(module, manager_url, mgr_username, mgr_password, validate_certs, display_name):
    transport_zones = get_transport_zones(module, manager_url, mgr_username, mgr_password, validate_certs)
    for transport_zone in transport_zones['results']:
        if transport_zone.__contains__('display_name') and transport_zone['display_name'] == display_name:
            return transport_zone
    return None

def check_for_update(module, manager_url, mgr_username, mgr_password, validate_certs, transport_zone_params):
    existing_transport_zone = get_tz_from_display_name(module, manager_url, mgr_username, mgr_password, validate_certs, transport_zone_params['display_name'])
    if existing_transport_zone is None:
        return False
    if existing_transport_zone.__contains__('transport_type') and transport_zone_params.__contains__('transport_type') and \
        existing_transport_zone['transport_type'] != transport_zone_params['transport_type']:
        return True
    return False


def main():
  argument_spec = vmware_argument_spec()
  argument_spec.update(display_name=dict(required=True, type='str'),
                        transport_type=dict(required=True, type='str'),
                        host_switch_mode=dict(required=False, type='str'),
                        host_switch_name=dict(required=False, type='str'),
                        nested_nsx=dict(required=False, type='boolean'),
                        uplink_teaming_policy_names=dict(required=False, type='list'),
                        transport_zone_profile_ids=dict(required=False, type='list'),
                        resource_type=dict(required=False),
                        description=dict(required=False),
                        state=dict(reauired=True, choices=['present', 'absent']))

  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
  transport_zone_params = get_transport_zone_params(module.params.copy())
  state = module.params['state']
  mgr_hostname = module.params['hostname']
  mgr_username = module.params['username']
  mgr_password = module.params['password']
  validate_certs = module.params['validate_certs']
  display_name = module.params['display_name']
  manager_url = 'https://{}/api/v1'.format(mgr_hostname)

  zone_dict = get_tz_from_display_name (module, manager_url, mgr_username, mgr_password, validate_certs, display_name)
  zone_id, revision = None, None
  if zone_dict:
      zone_id = zone_dict['id']
      revision = zone_dict['_revision']

  if state == 'present':
    headers = dict(Accept="application/json")
    headers['Content-Type'] = 'application/json'
    updated = check_for_update(module, manager_url, mgr_username, mgr_password, validate_certs, transport_zone_params)

    if not updated:
      # add the node
      if module.check_mode:
          module.exit_json(changed=True, debug_out=str(json.dumps(transport_zone_params)), id='12345')
      request_data = json.dumps(transport_zone_params)
      try:
          if zone_id:
              module.exit_json(changed=False, id=zone_id, message="Transport zone with display_name %s already exist."% module.params['display_name'])

          (rc, resp) = request(manager_url+ '/transport-zones', data=request_data, headers=headers, method='POST',
                                url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
      except Exception as err:
          module.fail_json(msg="Failed to add transport zone. Request body [%s]. Error[%s]." % (request_data, to_native(err)))
      #dict_resp = json.loads(resp)
      time.sleep(5)
      module.exit_json(changed=True, id=resp["id"], body= str(resp), message="Transport zone with display name %s created. " % (module.params['display_name']))
    else:
      if module.check_mode:
          module.exit_json(changed=True, debug_out=str(json.dumps(transport_zone_params)), id=zone_id)

      transport_zone_params['_revision'] = revision # update current revision
      request_data = json.dumps(transport_zone_params)
      id = zone_id
      try:
          (rc, resp) = request(manager_url+ '/transport-zones/%s' % id, data=request_data, headers=headers, method='PUT',
                                url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs, ignore_errors=True)
      except Exception as err:
          module.fail_json(msg="Failed to update transport zone with id %s. Request body [%s]. Error[%s]." % (id, request_data, to_native(err)))

      time.sleep(5)
      module.exit_json(changed=True, id=resp["id"], body= str(resp), message="Transport zone with zone id %s updated." % id)

  elif state == 'absent':
    # delete the array
    id = zone_id
    if id is None:
        module.exit_json(changed=False, msg='No transport zone exist with display name %s' % display_name)
    if module.check_mode:
        module.exit_json(changed=True, debug_out=str(json.dumps(transport_zone_params)), id=id)
    try:
        (rc, resp) = request(manager_url + "/transport-zones/%s" % id, method='DELETE',
                              url_username=mgr_username, url_password=mgr_password, validate_certs=validate_certs)
    except Exception as err:
        module.fail_json(msg="Failed to delete transport zone with id %s. Error[%s]." % (id, to_native(err)))

    time.sleep(5)
    module.exit_json(changed=True, object_name=id, message="Transport zone with zone id %s deleted." % id)


if __name__ == '__main__':
    main()
