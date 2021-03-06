#!/usr/bin/env python

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

"""
This program generates qpid-dispatch router configurations scripts
and support files.

The routers run on two hosts ('taj', and 'unused'). You can change 
their names in the definitions of the hosts dictionary. Hosts also
defines which router runs on each host.

A network of routers is defined to run on some number of host 
systems. This program emits:
 * Start scripts to start the routers on each host
 * Cleanup scripts to delete run-time artifacts on each host
 * Shell scripts that define variables for addressing ports on
   the host systems. [A twelve-router system may have nearly
   one hundred ports. File set.sh defines logical names for the
   ports that include the host:port pair. A console user running
   tests against this router network may then use $EA1_normal
   and $INTB_normal to target specific ports with no prior 
   knowledge of the host or port details.]
 * 2021-01-07
   - Add a TCP echo server connector to each router
   - Add TCP listeners for each router to each router

Using this code:

1. Edit hosts and the names of the routers to run on each.
2. In main define the common and specific configurations for each router.
3. Run the script.
4. The configurations will be in a time-of-day named directory.
5. Scripts produced will be:
  a. set.sh - a script to be dot sourced to give usable names for ports.
  b. unset.sh - undo set.sh
  c. run-taj.sh, run-unused.sh - scripts to launch the routers on your hosts.
     'qdrouterd' and 'ECHO_SERVER' must be installed and available from the
     command prompt.
  d. clean-taj.sh clean-unused.sh - remove common per-run output files.
  e. ps-eaf-forever.sh - script to monitor routers
  f. emitted script 'stop-taj.sh' kills the routers and servers.
6. Run your test
    simple_send -a $EA1_normal/multicast/q1 -m 1000
    simple_recv -a $EB2_normal/multicast/q1 -m 1000
"""

from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import datetime
import os
import sys
import traceback

IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    def dict_iteritems(d):
        return d.iteritems()
else:
    def dict_iteritems(d):
        return iter(d.items())


class Qdrouterd:
    """Emit a qdrouter config"""

    class Config(list):
        """
        List of ('section', {'name':'value', ...}).

        Fills in some default values automatically, see Qdrouterd.DEFAULTS
        """

        DEFAULTS = {
            'listener': {'host': '0.0.0.0', 'saslMechanisms': 'ANONYMOUS', 'idleTimeoutSeconds': '120',
                         'authenticatePeer': 'no', 'role': 'normal'},
            'connector': {'host': '127.0.0.1', 'saslMechanisms': 'ANONYMOUS', 'idleTimeoutSeconds': '120'},
            'router': {'mode': 'standalone', 'id': 'QDR', 'debugDumpFile': 'qddebug.txt'}
        }

        def sections(self, name):
            """Return list of sections named name"""
            return [p for n, p in self if n == name]

        @property
        def router_id(self):
            return self.sections("router")[0]["id"]

        def defaults(self):
            """Fill in default values in gconfiguration"""
            for name, props in self:
                if name in Qdrouterd.Config.DEFAULTS:
                    for n, p in dict_iteritems(Qdrouterd.Config.DEFAULTS[name]):
                        props.setdefault(n, p)

        def __str__(self):
            """Generate config file content. Calls default() first."""

            def tabs(level):
                return "    " * level

            def sub_elem(l, level):
                return "".join(["%s%s: {\n%s%s}\n" % (tabs(level), n, props(p, level + 1), tabs(level)) for n, p in l])

            def child(v, level):
                return "{\n%s%s}" % (sub_elem(v, level), tabs(level - 1))

            def props(p, level):
                return "".join(
                    ["%s%s: %s\n" % (tabs(level), k, v if not isinstance(v, list) else child(v, level + 1)) for k, v in
                     dict_iteritems(p)])

            self.defaults()
            return "".join(["%s {\n%s}\n" % (n, props(p, 1)) for n, p in self])

    def __init__(self, name=None, config=Config()):
        """
        @param name: name used for for output files, default to id from config.
        @param config: router configuration
        @keyword wait: wait for router to be ready (call self.wait_ready())
        """
        self.qconfig = Qdrouterd.Config(config)
        if not name:
            name = self.qconfig.router_id
        assert name
        default_log = [l for l in config if (l[0] == 'log' and l[1]['module'] == 'DEFAULT')]
        if not default_log:
            self.qconfig.append(
                (
                'log', {'module': 'DEFAULT', 'enable': 'info+', 'includeSource': 'true', 'outputFile': name + '.log'}))

    def get_config(self):
        return str(self.qconfig)

class Ports:
    """
    Dish out port numbers in sequence
    This function associates a (port, router, description) tuple
    and uses that information later to describe the router network.
    """

    def __init__(self):
        self.port = 21000
        self.port_scoreboard = []

    def get_port(self, router, description):
        self.port_scoreboard.append((self.port, router, description))
        self.port += 1
        return self.port - 1

    def show_ports(self, hostmap):
        res = ""
        for port, router, descr in self.port_scoreboard:
            host = ""
            for k, v in dict_iteritems(hostmap):
                if router in v:
                    host = k
                    break
            res += "port %d - %s %s %s\n" % (port, host, router, descr)
        return res

    def show_shell_set_script(self, hostmap):
        res = ""
        for port, router, descr in self.port_scoreboard:
            for k, v in dict_iteritems(hostmap):
                if router in v:
                    res += "%s=%s:%d\n" % (descr, k, port)
                    break
        return res

    def show_shell_unset_script(self, hostmap):
        res = ""
        for port, router, descr in self.port_scoreboard:
            for k, v in dict_iteritems(hostmap):
                if router in v:
                    res += "unset %s\n" % (descr)
                    break
        return res


def conn_host(connector_rtr, listener_rtr, hosts):
    """
    A router connector is being defined.
    If the listener is on the same host as the connecting router return localhost "127.0.0.1"
    else return the listening host name.
    :param connector_rtr:
    :param listener_rtr:
    :param hosts:
    :return:
    """
    cr = ""
    lr = ""
    for k, v in dict_iteritems(hosts):
        if connector_rtr in v:
            cr = k
        if listener_rtr in v:
            lr = k
    assert cr != ""
    assert lr != ""
    return "127.0.0.1" if cr == lr else lr


def main(argv):
    # Q: Where to put the generated files? A: odir
    od = "%s" % (datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    odir = os.path.join(os.getcwd(), od)
    try:
        os.makedirs(odir)
    except OSError as e:
        raise  # exit on any error

    # configuration common to all routers
    def router(name, mode, hosts, tcp_echo_server, tcp_listeners, connection, extra=None, extra2=None):
        config = [
            ('router', {'mode': mode, 'id': name, 'debugDumpFile': 'qddebug-' + name + '.txt'}),
            ('policy', {'maxConnections': '500', 'enableVhostPolicy': 'false', 'maxMessageSize': '100000', 'policyDir': '.'}),
            ('listener', {'port': ports.get_port(name, "%s_normal" % name)}),
            ('listener', {'port': ports.get_port(name, "%s_multitenant" % name), 'multiTenant': 'yes'}),
            ('listener', {'port': ports.get_port(name, "%s_routecontainer" % name),'role': 'route-container'}),
            ('listener', {'port': ports.get_port(name, "%s_http" % name), 'http': 'true'}),
            ('linkRoute', {'prefix': '0.0.0.0/link', 'direction': 'in', 'containerId': 'LRC'}),
            ('linkRoute', {'prefix': '0.0.0.0/link', 'direction': 'out', 'containerId': 'LRC'}),
            ('autoLink', {'address': '0.0.0.0/queue.waypoint', 'containerId': 'ALC', 'direction': 'in'}),
            ('autoLink', {'address': '0.0.0.0/queue.waypoint', 'containerId': 'ALC', 'direction': 'out'}),
            ('address', {'prefix': 'closest', 'distribution': 'closest'}),
            ('address', {'prefix': 'spread', 'distribution': 'balanced'}),
            ('address', {'prefix': 'multicast', 'distribution': 'multicast'}),
            ('address', {'prefix': '0.0.0.0/queue', 'waypoint': 'yes'}),
            ('log',
             {'module': 'ROUTER_CORE', 'enable': 'info+', 'includeSource': 'true', 'outputFile': name + '.log'}),
            ('log',
             {'module': 'HTTP', 'enable': 'trace+', 'includeSource': 'true', 'outputFile': name + '.log'}),
            connection
        ]

        if extra:
            config.append(extra)
        if extra2:
            config.append(extra2)

        # single connector to this router's echo server
        config.append( ('tcpConnector', {'host': '127.0.0.1',
                                         'port': tcp_echo_server[name],
                                         'address': "ES_" + name,
                                         'siteId': 'outtaSight'}) )

        # multiple listeners for every router's server
        for k, v in dict_iteritems(hosts):
            for rtr_v in v:
                portname = "%s_%s" % (name, rtr_v)
                config.append( ('tcpListener', {'host': '127.0.0.1',
                                                'port': tcp_listeners[portname],
                                                'address': "ES_" + rtr_v,
                                                'siteId': 'outtaSight'}))

        qdr = Qdrouterd(name, config)
        fn = os.path.join(odir, name + '.conf')
        with open(fn, 'w') as f:
            f.write(qdr.get_config())

    # initialize port pool
    ports = Ports()

    # common port numbers
    inter_router_portAB = ports.get_port("", "listener inter_router AB")
    inter_router_portBC = ports.get_port("", "listener inter_router BC")
    inter_router_portCD = ports.get_port("", "listener inter_router CD")
    edge_port_A = ports.get_port("", "listener edge A")
    edge_port_B = ports.get_port("", "listener edge B")
    edge_port_C = ports.get_port("", "listener edge C")
    edge_port_D = ports.get_port("", "listener edge D")

    # Select host on which each router runs
    hosts = {"taj":    ["INTA", "INTC", "EA1", "EB1", "EC1", "ED1"],
             "unused": ["INTB", "INTD", "EA2", "EB2", "EC2", "ED2"]}

    # allocate tcp echo server listener ports
    tcp_echo_server_listener_ports = {}
    for k, v in dict_iteritems(hosts):
        for rtr in v:
            tcp_echo_server_listener_ports[rtr] = ports.get_port(rtr, "Echo_server_listener_" + rtr)

    # allocate tcp adaptor listeners for router to access each server
    tcp_adaptor_listener_ports = {}
    for kl, vl in dict_iteritems(hosts):
        for rtr_vl in vl:
            for ks, vs in dict_iteritems(hosts):
                for rtr_vs in vs:
                    portname = "%s_%s" % (rtr_vl, rtr_vs)
                    tcp_adaptor_listener_ports[portname] = ports.get_port(rtr_vl, "Echo_listener_" + portname)

    # generate router configs
    router('INTA', 'interior', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('listener', {'role': 'inter-router', 'port': inter_router_portAB}),
           ('listener', {'role': 'edge', 'port': edge_port_A}))
    router('INTB', 'interior', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('listener', {'role': 'inter-router', 'port': inter_router_portBC}),
           ('connector', {'name': 'connectorToA', 'role': 'inter-router', 'port': inter_router_portAB,
                          'host': conn_host('INTB', 'INTA', hosts)}),
           ('listener', {'role': 'edge', 'port': edge_port_B}))
    router('INTC', 'interior', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('listener', {'role': 'inter-router', 'port': inter_router_portCD}),
           ('connector', {'name': 'connectorToB', 'role': 'inter-router', 'port': inter_router_portBC,
                          'host': conn_host('INTC', 'INTB', hosts)}),
           ('listener', {'role': 'edge', 'port': edge_port_C}))
    router('INTD', 'interior', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector', {'name': 'connectorToC', 'role': 'inter-router', 'port': inter_router_portCD,
                          'host': conn_host('INTD', 'INTC', hosts)}),
           ('listener', {'role': 'edge', 'port': edge_port_D}))
    router('EA1', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_A, 'host': conn_host('EA1', 'INTA', hosts)}))
    router('EA2', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_A, 'host': conn_host('EA2', 'INTA', hosts)}))
    router('EB1', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_B, 'host': conn_host('EB1', 'INTB', hosts)}))
    router('EB2', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_B, 'host': conn_host('EB2', 'INTB', hosts)}))
    router('EC1', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_C, 'host': conn_host('EC1', 'INTC', hosts)}))
    router('EC2', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_C, 'host': conn_host('EC2', 'INTC', hosts)}))
    router('ED1', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_D, 'host': conn_host('ED1', 'INTD', hosts)}))
    router('ED2', 'edge', hosts, tcp_echo_server_listener_ports, tcp_adaptor_listener_ports,
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_D, 'host': conn_host('ED2', 'INTD', hosts)}))

    # generate start scripts
    for k, v in dict_iteritems(hosts):
        name = os.path.join(odir, 'run-' + k + '.sh')
        with open(name, 'w') as f:
            f.write('#!/bin/bash\n')
            for rtr in v:
                f.write('echo Starting %s\n' % rtr)
                f.write('qdrouterd -c %s.conf &\n' % rtr)
                f.write('echo $!\n')
                f.write('ECHO_SERVER -p %d &\n' % tcp_echo_server_listener_ports[rtr])
                f.write('echo $!\n')
            os.chmod(name, 0o775)

    # generate cleanup scripts
    for k, v in dict_iteritems(hosts):
        name = os.path.join(odir, 'clean-' + k + '.sh')
        with open(name, 'w') as f:
            f.write('#!/bin/bash\n')
            for rtr in v:
                f.write('echo Cleaning %s\n' % rtr)
                f.write('rm %s.log\n' % rtr)
                f.write('rm qddebug-%s.txt\n' % rtr)
            f.write('echo Killing *ALL* qdrouterd ...\n')
            f.write("for pid in `ps -ef | grep qdrouterd | grep .conf | awk '{print $2}'` ; do echo $pid ; kill $pid ; done\n")
            f.write('echo Killing *ALL* echo servers ...\n')
            f.write("for pid in `ps -ef | grep ECHO_SERVER | grep python | awk '{print $2}'` ; do echo $pid ; kill $pid ; done\n")
            os.chmod(name, 0o775)

    # Show hosts and port number cheat sheet
    name = os.path.join(odir, 'config.txt')
    with open(name, 'w') as f:
        f.write("Hosts\n\n")
        for k, v in dict_iteritems(hosts):
            f.write("Host: %15s runs routers: %s\n" % (k, str(v)))
        f.write("\nPorts:\n\n")
        f.write(ports.show_ports(hosts))

    # write a shell script that defines variables for port functions
    name = os.path.join(odir, 'set.sh')
    with open(name, 'w') as f:
        f.write(ports.show_shell_set_script(hosts))

    # write a shell script that undefines variables for port functions
    name = os.path.join(odir, 'unset.sh')
    with open(name, 'w') as f:
        f.write(ports.show_shell_unset_script(hosts))
    return 0



if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
