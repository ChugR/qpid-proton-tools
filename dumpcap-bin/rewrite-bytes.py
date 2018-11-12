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

from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import traceback


def usage(argv):
    print("%s infile outfile\n" % str(argv[0]))


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def main_except(argv):
    if len(argv) != 3:
        usage(argv)
        raise ValueError("%s expects exactly two arguments." % str(argv[0]))
    fni = str(argv[1])
    fno = str(argv[2])
    offset = 0
    with open(fni, 'r') as fi:
        with open(fno, "w") as fo:
            fo.write("char rewrite_bytes[] = {")
            for line in fi:
                if line.startswith("0x"):
                    n0x = line.count("0x")
                    asci = ""
                    for i in range(1, n0x+1):
                        st = find_nth(line, "0x", i)
                        val = int(line[st:st+4], 16)
                        if val < 32 or val > 126:
                            asci += '.'
                        else:
                            asci += chr(val)
                    pad = ((8 - n0x) * 6) * ' '
                    pad2 = (8 - n0x) * ' '
                    fo.write( line.strip().replace(" };", ",") + pad + " /* off: " + str(offset) + "  " + asci + pad2 + " */\n " )
                    offset += line.count("0x")
            fo.write("};")


def main(argv):
    try:
        main_except(argv)
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
