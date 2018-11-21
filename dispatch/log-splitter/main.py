#!/usr/bin/env python

# Split a gigantic (or not) qpid-dispatch log file into
# files of traffic for each connection.

from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import traceback
from collections import defaultdict


class connection():
    def __init__(self, instance, conn_id):
        self.instance = instance
        self.conn_id = conn_id
        self.lines = []
        self.key_name = connection.keyname(instance, conn_id)
        self.transfers = 0
        self.router_open = ""


    @staticmethod
    def keyname(instance, conn_id):
        tmp = "0000000" + str(conn_id)
        return str(instance) + "." + tmp[-8:]

    def disp_name(self):
        return str(self.instance) + "_" + str(self.conn_id)


class LogFile:
    def __init__(self, fn, top_n=24):
        """
        Represent connections in a file
        :param fn: file name
        :param top_n: How many to print individually in summary
        """
        self.log_fn = fn    # file name
        self.top_n = top_n  # how many to report
        self.instance = 0   # incremented when router restarts in log file
        self.amqp_lines = 0 # server trace lines
        self.summary = ""   # printed to console, saved in summary.txt

        # restarts
        self.restarts = []

        # connections
        # dictionary of connection data
        # key = connection id: <instance>.<conn_id>    "0.3"
        # val = connection class object
        self.connections = {}

        # router_connections
        # list of received opens that suggest a router at the other end
        self.router_connections = []

        # errors
        # amqp errors in time order
        self.errors = []

        # sizemap - for organizing output by number of lines in connections
        # key = str(n_log_lines_in_connection)
        # val = list of connections
        # 1000 = [1.3, 1.5]
        #  500 = [1.1, 1.2, 1.4]
        self.sizemap = defaultdict(list)

        # sizelist - descending size of log line totals
        # [1000, 500]
        self.sizelist = []

        # conns_by_size
        # all connections in size descending order
        # [1.3, 1.5, 1.1, 1.2, 1.5]
        self.conns_by_size = []

        # histogram - count of connections with N logs < 10^index
        # [0] = N < 10^0
        # [1] = N < 10^1
        self.histogram = [0,0,0,0,0,0,0,0,0,0]
        self.hist_max = len(self.histogram) - 1

    def print(self, line='', end='\n'):
        self.summary += "%s%s" % (line, end)

    def parse_line(self, line):
        """
        Do minimum parsing on line.
        If container name then bump instance value
        If server trace then get conn_id and add line to connections data
        :param line:
        :return:
        """
        key1 = "SERVER (info) Container Name:"  # Normal 'router is starting' restart discovery line
        key2 = "SERVER (trace) ["  # AMQP traffic
        key3 = "@error(29)"
        key4 = "<- @open(16)"
        key5 = ':product="qpid-dispatch-router"'
        key6 = "@transfer"

        if key1 in line:
            self.instance += 1
            self.restarts.append(line)
        else:
            idx = line.find(key2)
            if idx > 0:
                self.amqp_lines += 1
                idx += len(key2)
                eidx = line.find("]", idx + 1)
                conn_id = line[idx:eidx]
                keyname = connection.keyname(self.instance, conn_id)
                if keyname not in self.connections:
                    self.connections[keyname] = connection(self.instance, conn_id)
                self.connections[keyname].lines.append(line)
                # router hint
                if key4 in line and key5 in line:
                    self.router_connections.append(self.connections[keyname])
                    self.connections[keyname].router_open = line
                elif key6 in line:
                    self.connections[keyname].transfers += 1
        if key3 in line:
            self.errors.append(line)

    def log_of(self, x):
        """
        calculate nearest power of 10 > x
        :param x:
        :return:
        """
        for i in range(self.hist_max):
            if x < 10 ** i:
                return i
        return self.hist_max

    def summarize_connections(self):
        self.print("File               : %s" % self.log_fn)
        self.print("Router starts      : %8d" % self.instance)
        self.print("Connections        : %8d" % len(self.connections))
        self.print("Router connections : %8d" % len(self.router_connections))
        self.print("AMQP log lines     : %8d" % self.amqp_lines)
        self.print("AMQP errors        : %8d" % len(self.errors))

        # create size map. index is size, list holds all connections of that many log lines
        for k, v in dict_iteritems(self.connections):
            self.sizemap[str(len(v.lines))].append(v)
        # create a sorted list of sizes in sizemap
        sl = list(dict_iterkeys(self.sizemap))
        sli = [int(k) for k in sl]
        self.sizelist = sorted(sli, reverse=True)
        # create grand list of all connections
        for cursize in self.sizelist:
            lsm = self.sizemap[str(cursize)]
            for ls in lsm:
                self.conns_by_size.append(ls)

        # Restarts
        self.print()
        self.print("Router starts")
        for i in range(1, (self.instance + 1)):
            rr = self.restarts[i-1]
            self.print("(%d) - %s" % (i, rr), end='')

        # Report top hitters
        self.print()
        self.print("Most active connections by total log lines")
        self.print("    Lines  Connection")
        for i in range(min(self.top_n, len(self.conns_by_size))):
            self.print("%9d  %s" % (len(self.conns_by_size[i].lines), self.conns_by_size[i].disp_name()))

        # interrouter connections
        self.print()
        self.print("Probable router connections")
        for rc in self.router_connections:
            n = len(rc.lines)
            logn = self.log_of(n)
            self.print("Connection: %s, directory: 10e%d, total log lines: %d, transfers: %d" %
                  (rc.disp_name(), logn, n, rc.transfers))
            self.print("%s" % rc.router_open, end='')

        # histogram
        for cursize in self.sizelist:
            self.histogram[self.log_of(cursize)] += len(self.sizemap[str(cursize)])
        self.print()
        self.print("Log lines per connection distribution")
        for i in range(1, self.hist_max):
            self.print("N <  10e%d : %d" %(i, self.histogram[i]))
        self.print("N >= 10e%d : %d" % ((self.hist_max - 1), self.histogram[self.hist_max]))

        # errors
        self.print()
        self.print("AMQP Errors:")
        for er in self.errors:
            self.print("%s" % er, end='')

    def odir(self):
        return os.path.join(os.getcwd(), (self.log_fn + ".splits"))

    def write_subfiles(self):
        # Q: Where to put the generated files? A: odir
        odir = self.odir()
        odirs = ['dummy'] # dirs indexed by log of n-lines
        try:
            os.makedirs(odir)
            for i in range(1, self.hist_max):
                nrange = ("10e%d" % (i))
                ndir = os.path.join(odir, nrange)
                os.makedirs(ndir)
                odirs.append(ndir)

            for k, c in dict_iteritems(self.connections):
                cdir = odirs[self.log_of(len(c.lines))]
                opath = os.path.join(cdir, (c.disp_name() + ".log"))
                with open(opath, 'w') as f:
                    for l in c.lines:
                        f.write(l)
            spath = os.path.join(odir, "summary.txt")
            with open(spath, 'w') as f:
                f.write(self.summary)
            spath = os.path.join(odir, "statistics.txt")
            with open(spath, 'w') as f:
                f.write("Connection  LogLines Transfers Directory IsRouter?\n")
                for rc in self.conns_by_size:
                    n = len(rc.lines)
                    logn = self.log_of(n)
                    isrtr = "yes" if rc.router_open != "" else ""
                    f.write("%10s %9d %9d 10e%d      %s\n" %
                               (rc.disp_name(), n, rc.transfers, logn, isrtr))
        except OSError as e:
            raise  # exit on any error


# py 2-3 compat

IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    def dict_iteritems(d):
        return d.iteritems()
    def dict_iterkeys(d):
        return d.iterkeys()
else:
    def dict_iteritems(d):
        return iter(d.items())
    def dict_iterkeys(d):
        return iter(d.keys())


#
#
def main_except(argv):
    """
    Given a log file name, split the file into per-connection sub files
    """
    if len(argv) != 2:
        sys.exit('Usage: %s log-file-name' % argv[0])

    log_files = []

    # process the log files and add the results to router_array
    for log_i in range(0, len(sys.argv) - 1):
        log_fn = sys.argv[log_i + 1]

        if not os.path.exists(log_fn):
            sys.exit('ERROR: log file %s was not found!' % log_fn)

        # parse the log file
        with open(log_fn, 'r') as infile:
            lf = LogFile(log_fn)
            odir = lf.odir()
            if os.path.exists(odir):
                sys.exit('ERROR: output directory %s exists' % odir)
            log_files.append(lf)
            for line in infile:
                lf.parse_line(line)

        # write output
        for lf in log_files:
            lf.summarize_connections() # prints to console. Want web page?
            print("%s" % lf.summary)
            lf.write_subfiles()        # generates split files one-per-connection
        pass

def main(argv):
    try:
        main_except(argv)
        return 0
    except Exception as e:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
