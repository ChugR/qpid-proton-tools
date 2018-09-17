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


def main_except(argv):
    if len(argv) != 3:
        usage(argv)
        raise ValueError("%s expects exactly two arguments." % str(argv[0]))
    fni = str(argv[1])
    fno = str(argv[2])
    with open(fni, 'r') as fi:
        with open(fno, "w") as fo:
            fo.write("char rewrite_bytes[] = {")
            for line in fi:
                if line.startswith("0x"):
                    fo.write(line.replace(" };", ","))
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
