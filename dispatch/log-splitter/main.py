#!/usr/bin/env python

# Split a gigantic (or not) log file into files of traffic for each connection.
# Identify probable router and broker connections, QpidJMS client connections,
# and AMQP errors. Create lists of connections sorted by log line and by transfer counts.
# Emit a web page summarizing the results.

from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import cgi
import os
import sys
import traceback
from collections import defaultdict


class connection():
    def __init__(self, instance, conn_id, logfile):
        self.instance = instance
        self.conn_id = conn_id
        self.logfile = logfile
        self.lines = []
        self.key_name = connection.keyname(instance, conn_id)
        self.transfers = 0
        self.peer_open = ""
        self.peer_type = ""
        self.log_n_lines = 0
        self.log_n_dir = ""
        self.file_name = ""
        self.path_name = ""

    @staticmethod
    def keyname(instance, conn_id):
        tmp = "0000000" + str(conn_id)
        return str(instance) + "." + tmp[-8:]

    def disp_name(self):
        return str(self.instance) + "_" + str(self.conn_id)

    def generate_paths(self):
        self.log_n_dir = "10e%d" % self.log_n_lines
        self.file_name = self.disp_name() + ".log"
        self.path_name = self.log_n_dir + "/" + self.file_name


class LogFile:
    def __init__(self, fn, top_n=24):
        """
        Represent connections in a file
        :param fn: file name
        :param
        """
        self.log_fn = fn    # file name
        self.top_n = top_n  # how many to report
        self.instance = 0   # incremented when router restarts in log file
        self.amqp_lines = 0 # server trace lines
        self.transfers = 0  # server transfers

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

        # broker connections
        # list of received opens that suggest a broker at the other end
        self.broker_connections = []

        # errors
        # amqp errors in time order
        self.errors = []

        # conns_by_size_transfer
        # all connections in transfer size descending order
        self.conns_by_size_transfer = []

        # conns_by_size_loglines
        # all connections in log_lines size descending order
        self.conns_by_size_loglines = []

        # histogram - count of connections with N logs < 10^index
        # [0] = N < 10^0
        # [1] = N < 10^1
        self.histogram = [0,0,0,0,0,0,0,0,0,0]
        self.hist_max = len(self.histogram) - 1

    def parse_identify(self, text, line, before_col=70):
        """
        Look for text in line but make sure it's not in the body of some message,
        :param text:
        :param line:
        :param before_col: limit on how far to search into line
        """
        st = line.find(text, 0, (before_col + len(text)))
        if st < 0:
            return False
        return st < 70

    def parse_line(self, line):
        """
        Do minimum parsing on line.
        If container name then bump instance value
        If server trace then get conn_id and add line to connections data
        :param line:
        :return:
        """
        key_sstart = "SERVER (info) Container Name:"  # Normal 'router is starting' restart discovery line
        key_strace = "SERVER (trace) ["  # AMQP traffic
        key_error = "@error(29)"
        key_openin = "<- @open(16)"
        key_xfer = "@transfer"
        key_prod_dispatch = ':product="qpid-dispatch-router"'
        key_prod_aartemis = ':product="apache-activemq-artemis"'
        key_prod_aqpidcpp = ':product="qpid-cpp"'
        key_prod_aqpidjms = ':product="QpidJMS"'

        if self.parse_identify(key_sstart, line):
            self.instance += 1
            self.restarts.append(line)
        else:
            if self.parse_identify(key_strace, line):
                self.amqp_lines += 1
                idx = line.find(key_strace)
                idx += len(key_strace)
                eidx = line.find("]", idx + 1)
                conn_id = line[idx:eidx]
                keyname = connection.keyname(self.instance, conn_id)
                if keyname not in self.connections:
                    self.connections[keyname] = connection(self.instance, conn_id, self)
                curr_conn = self.connections[keyname]
                curr_conn.lines.append(line)
                # router hint
                if key_openin in line:
                    # inbound open
                    if key_prod_dispatch in line:
                        self.router_connections.append(curr_conn)
                        curr_conn.peer_open = line
                        curr_conn.peer_type = key_prod_dispatch
                    elif key_prod_aqpidjms in line:
                            curr_conn.peer_type = key_prod_aqpidjms
                    else:
                        for k in [key_prod_aartemis, key_prod_aqpidcpp]:
                            if k in line:
                                self.broker_connections.append(curr_conn)
                                curr_conn.peer_open = line
                                curr_conn.peer_type = k
                elif self.parse_identify(key_xfer, line):
                    self.transfers += 1
                    curr_conn.transfers += 1
        if key_error in line:
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

    def sort_sizes(self, sortfunc1, sortfunc2):
        smap = defaultdict(list)
        conns_by_size = []
        # create size map. index is size, list holds all connections of that many transfers
        for k, v in dict_iteritems(self.connections):
            smap[str(sortfunc1(v))].append(v)
        # create a sorted list of sizes in sizemap
        sl = list(dict_iterkeys(smap))
        sli = [int(k) for k in sl]
        slist = sorted(sli, reverse=True)
        # create grand list of all connections
        for cursize in slist:
            lsm = smap[str(cursize)]
            lsm = sorted(lsm, key = sortfunc2, reverse=True)
            #lsm = sorted(lsm, key = lambda x: int(x.conn_id))
            for ls in lsm:
                conns_by_size.append(ls)
        return conns_by_size


    def summarize_connections(self):
        # sort connections based on transfer count and on n log lines
        self.conns_by_size_transfer = self.sort_sizes(lambda x: x.transfers, lambda x: len(x.lines))
        self.conns_by_size_loglines = self.sort_sizes(lambda x: len(x.lines), lambda x: x.transfers)

        # compute log_n and file name facts for all connections
        for k, v in dict_iteritems(self.connections):
            v.log_n_lines = self.log_of(len(v.lines))
            v.generate_paths()

        # Write the web doc to stdout
        print ("""<!DOCTYPE html>
        <html>
        <head>
        <title>%s qpid-dispatch log split</title>

        <style>
            * { 
            font-family: sans-serif; 
        }
        table {
            border-collapse: collapse;
        }
        table, td, th {
            border: 1px solid black;
            padding: 3px;
        }
        </style>
""" % self.log_fn)

        print("""
<h3>Contents</h3>
<table>
<tr> <th>Section</th>                                                     <th>Description</th> </tr>
<tr><td><a href=\"#c_summary\"        >Summary</a></td>                   <td>Summary</td></tr>
<tr><td><a href=\"#c_restarts\"       >Router restarts</a></td>           <td>Router reboot records</td></tr>
<tr><td><a href=\"#c_router_conn\"    >Interrouter connections</a></td>   <td>Probable interrouter connections</td></tr>
<tr><td><a href=\"#c_broker_conn\"    >Broker connections</a></td>        <td>Probable broker connections</td></tr>
<tr><td><a href=\"#c_errors\"         >AMQP errors</a></td>               <td>AMQP errors</td></tr>
<tr><td><a href=\"#c_conn_xfersize\"  >Conn by N transfers</a></td>       <td>Connections sorted by transfer log count</td></tr>
<tr><td><a href=\"#c_conn_xfer0\"     >Conn with no transfers</a></td>    <td>Connections with no transfers</td></tr>
<tr><td><a href=\"#c_conn_logsize\"   >Conn by N log lines</a></td>       <td>Connections sorted by total log line count</td></tr>
</table>
<hr>
""")
        print("<a name=\"c_summary\"></a>")
        print("<table>")
        print("<tr><th>Statistic</th>          <th>Value</th></tr>")
        print("<tr><td>File</td>               <td>%s</td></tr>" % self.log_fn)
        print("<tr><td>Router starts</td>      <td>%s</td></tr>" % str(self.instance))
        print("<tr><td>Connections</td>        <td>%s</td></tr>" % str(len(self.connections)))
        print("<tr><td>Router connections</td> <td>%s</td></tr>" % str(len(self.router_connections)))
        print("<tr><td>AMQP log lines</td>     <td>%s</td></tr>" % str(self.amqp_lines))
        print("<tr><td>AMQP errors</td>        <td>%s</td></tr>" % str(len(self.errors)))
        print("<tr><td>AMQP transfers</td>     <td>%s</td></tr>" % str(self.transfers))
        print("</table>")
        print("<hr>")

        # Restarts
        print("<a name=\"c_restarts\"></a>")
        print("<h3>Restarts</h3>")
        for i in range(1, (self.instance + 1)):
            rr = self.restarts[i-1]
            print("(%d) - %s<br>" % (i, rr), end='')
        print("<hr>")

        # interrouter connections
        print("<a name=\"c_router_conn\"></a>")
        print("<h3>Probable inter-router connections</h3>")
        print("<table>")
        print("<tr><th>Connection</th> <th>Transfers</th> <th>Log lines</th> <th>AMQP Open<th></tr>")
        for rc in self.router_connections:
            print("<tr><td><a href=\"%s/%s\">%s</a></td><td>%d</td><td>%d</td><td>%s</td></tr>" %
                  (rc.logfile.odir(), rc.path_name, rc.disp_name(), rc.transfers, len(rc.lines),
                   cgi.escape(rc.peer_open)))
        print("</table>")
        print("<hr>")

        # broker connections
        print("<a name=\"c_broker_conn\"></a>")
        print("<h3>Probable broker connections</h3>")
        print("<table>")
        print("<tr><th>Connection</th> <th>Transfers</th> <th>Log lines</th> <th>AMQP Open<th></tr>")
        for rc in self.broker_connections:
            print("<tr><td><a href=\"%s/%s\">%s</a></td><td>%d</td><td>%d</td><td>%s</td></tr>" %
                  (rc.logfile.odir(), rc.path_name, rc.disp_name(), rc.transfers, len(rc.lines),
                   cgi.escape(rc.peer_open)))
        print("</table>")
        print("<hr>")

        ## histogram
        #for cursize in self.sizelist:
        #    self.histogram[self.log_of(cursize)] += len(self.sizemap[str(cursize)])
        #print()
        #print("Log lines per connection distribution")
        #for i in range(1, self.hist_max):
        #    print("N <  10e%d : %d" %(i, self.histogram[i]))
        #print("N >= 10e%d : %d" % ((self.hist_max - 1), self.histogram[self.hist_max]))

        # errors
        print("<a name=\"c_errors\"></a>")
        print("<h3>AMQP errors</h3>")
        print("<table>")
        print("<tr><th>AMQP error</th></tr>")
        for er in self.errors:
            print("<tr><td>%s</td></tr>" % er.strip())
        print("</table>")
        print("<hr>")

    def odir(self):
        return os.path.join(os.getcwd(), (self.log_fn + ".splits"))

    def write_subfiles(self):
        # Q: Where to put the generated files? A: odir
        odir = self.odir()
        odirs = ['dummy'] # dirs indexed by log of n-lines

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

        print("<a name=\"c_conn_xfersize\"></a>")
        print("<h3>Connections by transfer count</h3>")
        print("<table>")
        print("<tr><th>Connection</th> <th>Transfers</th> <th>Log lines</th> <th>Type</th> <th>AMQP detail<th></tr>")
        for rc in self.conns_by_size_transfer:
            if rc.transfers > 0:
                print("<tr><td><a href=\"%s/%s\">%s</a></td> <td>%d</td> <td>%d</td> <td>%s</td> <td>%s</td></tr>" %
                      (rc.logfile.odir(), rc.path_name, rc.disp_name(), rc.transfers, len(rc.lines),
                       rc.peer_type, cgi.escape(rc.peer_open)))
        print("</table>")
        print("<hr>")

        print("<a name=\"c_conn_xfer0\"></a>")
        print("<h3>Connections with no AMQP transfers</h3>")
        print("<table>")
        print("<tr><th>Connection</th> <th>Transfers</th> <th>Log lines</th> <th>Type</th> <th>AMQP detail<th></tr>")
        for rc in self.conns_by_size_transfer:
            if rc.transfers == 0:
                print("<tr><td><a href=\"%s/%s\">%s</a></td> <td>%d</td> <td>%d</td> <td>%s</td> <td>%s</td></tr>" %
                      (rc.logfile.odir(), rc.path_name, rc.disp_name(), rc.transfers, len(rc.lines),
                       rc.peer_type, cgi.escape(rc.peer_open)))
        print("</table>")
        print("<hr>")

        print("<a name=\"c_conn_logsize\"></a>")
        print("<h3>Connections by total log line count</h3>")
        print("<table>")
        print("<tr><th>Connection</th> <th>Transfers</th> <th>Log lines</th> <th>Type</th> <th>AMQP detail<th></tr>")
        for rc in self.conns_by_size_loglines:
            print("<tr><td><a href=\"%s/%s\">%s</a></td> <td>%d</td> <td>%d</td> <td>%s</td> <td>%s</td></tr>" %
                  (rc.logfile.odir(), rc.path_name, rc.disp_name(), rc.transfers, len(rc.lines),
                   rc.peer_type, cgi.escape(rc.peer_open)))
        print("</table>")
        print("<hr>")


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
