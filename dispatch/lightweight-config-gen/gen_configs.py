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
Swiped mostly from qpid-dispatch/tests
Emit config files:
 * Use fixed port numbers
 * Select the host on which each router runs
 * Execute the script to generate the config in current directory

 * To clean everything back to scratch:
   git clean -dfx
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
                'log', {'module': 'DEFAULT', 'enable': 'trace+', 'includeSource': 'true', 'outputFile': name + '.log'}))

    def get_config(self):
        return str(self.qconfig)


class Ports:
    """Dish out port numbers in sequence"""

    def __init__(self):
        self.port = 21000
        self.port_scoreboard = []

    def get_port(self, who=''):
        self.port_scoreboard.append("port %d - %s" % (self.port, who))
        self.port += 1
        return self.port - 1

    def show_ports(self):
        return "\n".join(self.port_scoreboard) + "\n"


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
    def router(name, mode, connection, extra=None):
        config = [
            ('router', {'mode': mode, 'id': name, 'debugDumpFile': 'qddebug-' + name + '.txt'}),
            ('listener', {'port': ports.get_port("%s listener normal" % name), 'stripAnnotations': 'no'}),
            ('listener', {'port': ports.get_port("%s listener multiTenant" % name), 'stripAnnotations': 'no',
                          'multiTenant': 'yes'}),
            ('listener', {'port': ports.get_port("%s listener route-container" % name), 'stripAnnotations': 'no',
                          'role': 'route-container'}),
            ('linkRoute', {'prefix': '0.0.0.0/link', 'direction': 'in', 'containerId': 'LRC'}),
            ('linkRoute', {'prefix': '0.0.0.0/link', 'direction': 'out', 'containerId': 'LRC'}),
            ('autoLink', {'addr': '0.0.0.0/queue.waypoint', 'containerId': 'ALC', 'direction': 'in'}),
            ('autoLink', {'addr': '0.0.0.0/queue.waypoint', 'containerId': 'ALC', 'direction': 'out'}),
            ('address', {'prefix': 'closest', 'distribution': 'closest'}),
            ('address', {'prefix': 'spread', 'distribution': 'balanced'}),
            ('address', {'prefix': 'multicast', 'distribution': 'multicast'}),
            ('address', {'prefix': '0.0.0.0/queue', 'waypoint': 'yes'}),
            ('log',
             {'module': 'ROUTER_CORE', 'enable': 'info+', 'includeSource': 'true', 'outputFile': name + '.log'}),
            connection
        ]

        if extra:
            config.append(extra)
        qdr = Qdrouterd(name, config)
        fn = os.path.join(odir, name + '.conf')
        with open(fn, 'w') as f:
            f.write(qdr.get_config())


    # initialize port pool
    ports = Ports()

    # common port numbers
    inter_router_port = ports.get_port("listener inter_router")
    edge_port_A = ports.get_port("listener edge A")
    edge_port_B = ports.get_port("listener edge B")

    # Select host on which each router runs
    hosts = {"taj": ["INT.A", "EA1", "EB1"],
             "ratchet": ["INT.B", "EA2", "EB2"]}

    # generate router configs
    router('INT.A', 'interior',
           ('listener', {'role': 'inter-router', 'port': inter_router_port}),
           ('listener', {'role': 'edge', 'port': edge_port_A}))
    router('INT.B', 'interior',
           ('connector', {'name': 'connectorToA', 'role': 'inter-router', 'port': inter_router_port,
                          'host': conn_host('INT.B', 'INT.A', hosts)}),
           ('listener', {'role': 'edge', 'port': edge_port_B}))
    router('EA1', 'edge',
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_A, 'host': conn_host('EA1', 'INT.A', hosts)}))
    router('EA2', 'edge',
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_A, 'host': conn_host('EA2', 'INT.A', hosts)}))
    router('EB1', 'edge',
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_B, 'host': conn_host('EB1', 'INT.B', hosts)}))
    router('EB2', 'edge',
           ('connector',
            {'name': 'uplink', 'role': 'edge', 'port': edge_port_B, 'host': conn_host('EB2', 'INT.B', hosts)}))

    # generate start scripts
    for k, v in dict_iteritems(hosts):
        name = os.path.join(odir, 'run-' + k + '.sh')
        with open(name, 'w') as f:
            f.write('#!/bin/bash\n')
            for rtr in v:
                f.write('echo Starting %s\n' % rtr)
                f.write('qdrouterd -c %s.conf &\n' % rtr)
                f.write('echo $!\n')
            os.chmod(name, 0o775)

    # generate cleanup scripts
    for k, v in dict_iteritems(hosts):
        name = os.path.join(odir, 'clean-' + k + '.sh')
        with open(name, 'w') as f:
            f.write('#!/bin/bash\n')
            for rtr in v:
                f.write('echo Cleaning %s\n' % rtr)
                f.write('rm %s.log &\n' % rtr)
                f.write('rm qddebug-%s.txt &\n' % rtr)
            os.chmod(name, 0o775)

    # Show hosts and port number cheat sheet
    name = os.path.join(odir, 'config.txt')
    with open(name, 'w') as f:
        f.write("Hosts\n\n")
        for k, v in dict_iteritems(hosts):
            f.write("Host: %15s runs routers: %s\n" % (k, str(v)))
        f.write("\nPorts:\n\n")
        f.write(ports.show_ports())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
