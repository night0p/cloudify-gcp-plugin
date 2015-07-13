# #######
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
from cloudify import ctx
from cloudify.decorators import operation

from gcp.compute import constants
from gcp.compute import utils
from gcp.gcp import GoogleCloudPlatform
from gcp.gcp import check_response


class FirewallRule(GoogleCloudPlatform):
    def __init__(self,
                 config,
                 logger,
                 firewall,
                 network):
        """
        Create Firewall rule object

        :param config:
        :param logger:
        :param firewall: firewall dictionary with a following structure:
        firewall = {'name': 'firewallname',
                    'allowed: [{ 'IPProtocol': 'tcp', 'ports': ['80']}],
                    'sourceRanges':['0.0.0.0/0'],
                    'sourceTags':['tag'], (optional)
                    'targetTags':['tag2'] (optional)
                    }
        ref. https://cloud.google.com/compute/docs/reference/latest/firewalls
        :param network: network name the firewall rule is connected to
        """
        super(FirewallRule, self).__init__(config, logger, firewall['name'])
        self.firewall = firewall
        self.network = network

    @check_response
    def create(self):
        """
        Create GCP firewall rule in a GCP network.
        Global operation.

        :return: REST response with operation responsible for the firewall rule
        creation process and its status
        """
        self.logger.info(
            'Create firewall rule {0} in network {1}'.format(
                self.name,
                self.network))

        self.firewall['network'] = 'global/networks/{0}'.format(self.network)
        return self.discovery.firewalls().insert(
            project=self.project,
            body=self.firewall).execute()

    @check_response
    def delete(self):
        """
        Delete GCP firewall rule from GCP network.
        Global operation.

        :return: REST response with operation responsible for the firewall rule
        deletion process and its status
        """
        self.logger.info(
            'Delete firewall rule {0} from network {1}'.format(
                self.name,
                self.network))

        return self.discovery.firewalls().delete(
            project=self.project,
            firewall=self.firewall['name']).execute()

    @check_response
    def update(self):
        """
        Update GCP firewall rule.
        Global operation.

        :return: REST response with operation responsible for the firewall rule
        update process and its status
        """
        self.logger.info('Update firewall rule {0}'.format(self.name))

        return self.discovery.firewalls().update(
            project=self.project,
            firewall=self.firewall['name'],
            body=self.firewall).execute()

    @check_response
    def list(self):
        """
        List GCP firewall rules in all networks.

        :return: REST response with list of firewall rules in a project
        """
        self.logger.info(
            'List firewall rules in project {0}'.format(self.project))

        return self.discovery.firewalls().list(
            project=self.project).execute()


@operation
@utils.throw_cloudify_exceptions
def create(gcp_config, firewall_rule, **kwargs):
    network_name = utils.get_gcp_resource_name(gcp_config['network'])
    firewall_rule['name'] = utils.get_firewall_rule_name(network_name,
                                                         firewall_rule)
    firewall = FirewallRule(gcp_config,
                            ctx.logger,
                            firewall=firewall_rule,
                            network=network_name)

    firewall.create()
    ctx.instance.runtime_properties[constants.NAME] = firewall.name


@operation
@utils.throw_cloudify_exceptions
def delete(gcp_config, **kwargs):
    firewall_name = ctx.instance.runtime_properties.get(constants.NAME, None)
    if not firewall_name:
        return
    network_name = utils.get_gcp_resource_name(gcp_config['network'])
    firewall = FirewallRule(gcp_config,
                            ctx.logger,
                            firewall={'name': firewall_name},
                            network=network_name)
    firewall.delete()
    ctx.instance.runtime_properties.pop(constants.NAME, None)


@operation
@utils.throw_cloudify_exceptions
def create_security_group(gcp_config, rules, **kwargs):
    firewall = utils.create_firewall_structure_from_rules(
        gcp_config['network'],
        rules)
    ctx.instance.runtime_properties[constants.TARGET_TAGS] = \
        firewall[constants.TARGET_TAGS]
    ctx.instance.runtime_properties[constants.SOURCE_TAGS] = \
        firewall[constants.SOURCE_TAGS]
    firewall = FirewallRule(gcp_config,
                            ctx.logger,
                            firewall,
                            gcp_config['network'])
    firewall.create()
    ctx.instance.runtime_properties[constants.NAME] = firewall.name


@operation
@utils.throw_cloudify_exceptions
def delete_security_group(gcp_config, **kwargs):
    ctx.instance.runtime_properties.pop(constants.TARGET_TAGS, None)
    ctx.instance.runtime_properties.pop(constants.SOURCE_TAGS, None)
    delete(gcp_config, **kwargs)