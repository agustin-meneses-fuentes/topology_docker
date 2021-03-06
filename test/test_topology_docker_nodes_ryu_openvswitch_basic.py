# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Test for basic switching behaviour using Ryu + Openvswitch.
Runs the simple_switch ryu application
which makes two switches behave like a single switch by forwarding packets to
the controller.
"""

import pytest
import time
from subprocess import check_output

TOPOLOGY = """
#             +-------+
#             |       |
#             |  ryu  |
#             |       |
#             +-------+
#                 |
#             +-------+
#             |  sw1  |
#             +-------+
#             |       |
#      +-------+     +-------+
#      |  hs1  |     |  hs2  |
#      +-------+     +-------+


# Nodes
[type=ryu name="Ryu"] ryu
[type=openvswitch name="Switch 1"] sw1
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2

# Ports
[ipv4="10.0.10.1/24" up=True] ryu:1
[ipv4="10.0.10.2/24" up=True] sw1:1
[up=True] sw1:2
[up=True] sw1:3

# Hosts in same network
[ipv4="192.168.0.1/24" up=True] hs1:1
[ipv4="192.168.0.2/24" up=True] hs2:1

# Links
ryu:1 -- sw1:1
sw1:2 -- hs1:1
sw1:3 -- hs2:1
"""


@pytest.mark.skipif(
    'openvswitch' not in check_output('lsmod').decode('utf-8'),
    reason='Requires Open vSwitch kernel module.')
def test_controller_link(topology):

    ryu = topology.get('ryu')
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')
    sw1 = topology.get('sw1')

    assert ryu is not None
    assert hs1 is not None
    assert hs2 is not None
    assert sw1 is not None

    # ---- OVS Setup ----

    # Configuration:
    # - Create a bridge
    # - Bring up ovs interface
    # - Add the front port connecting to the controller
    # - Drop packets if the connection to controller fails
    # - Remove the front port's IP address
    # - Add the fronts port connecting to the hosts
    # - Give the virtual switch an IP address
    # - Connect to the OpenFlow controller
    commands = """
    ovs-vsctl add-br br0
    ip link set br0 up
    ovs-vsctl add-port br0 1
    ovs-vsctl set-fail-mode br0 secure
    ifconfig 1 0 up
    ovs-vsctl add-port br0 2
    ovs-vsctl add-port br0 3
    ifconfig 2 0 up
    ifconfig 3 0 up
    ifconfig br0 10.0.10.2 netmask 255.255.255.0 up
    ovs-vsctl set-controller br0 tcp:10.0.10.1:6633
    """
    sw1.libs.common.assert_batch(commands)

    # Wait for OVS to connect to controller
    time.sleep(5)

    # Assert that switch is connected to Ryu
    vsctl_sw1_show = sw1('ovs-vsctl show')
    assert 'is_connected: true' in vsctl_sw1_show

    # Test simple_switch with pings between hs1 and hs2
    ping_hs2 = hs1('ping -c 1 192.168.0.2')
    assert '1 packets transmitted, 1 received' in ping_hs2

    ping_hs1 = hs2('ping -c 1 192.168.0.1')
    assert '1 packets transmitted, 1 received' in ping_hs1
