#!/usr/bin/env python
#
# Version 0.1

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

# This code reads the AMQP 1.0 xml definitions and presents organized
# and cross referenced content in a web page.
#
# The page layout generally follows the layout of the AMQP 1.0 spec.
#
# The xml files are parsed:
#
# codec/types.xml
#  only primitive types. generates simple tables
#
# messaging.xml
#  sections: message-format, delivery-state, addressing
#
# transport.xml
#  sections: performatives, definitions
#
# Types
#  primitive
#  composite: descriptor and 1..n fields
#  restricted:
#    enumerations: 1..n choice
#    id: 0..1 descriptors and 0 fields
#
from __future__ import print_function
import sys, optparse, os, time
import xml.etree.ElementTree as ET

#
# construct data stores
typesPrimitive = []
typesComposite = []
typesDescribed = []

typesAll = []

provided = {} # {'name' : [type, type] with provides=name

class XmlStore():
    def __init__(self, filename):
        self.filename = filename
        self.tree = ET.parse(os.path.join(os.path.dirname(__file__), filename))
        self.root = self.tree.getroot()  # root=Element 'amqp'
        self.trimNamespace(self.root)
        self.sections = self.root.findall("section")
        self.types = []
        for section in self.sections:
            ltypes = section.findall("type")
            for type in ltypes:
                # decorate and categorize each type
                type.text = section.get("name")
                typesAll.append(type)
                if type.get("class") == "primitive":
                    typesPrimitive.append(type)
                else:
                    descr = type.find("descriptor")
                    if descr is None:
                        typesComposite.append(type)
                    else:
                        typesDescribed.append(type)
                provides = type.get("provides")
                if provides is not None:
                    if not provides in provided:
                        provided[provides] = []
                    provided[provides] += type
            self.types += section.findall("type")

    def trimNamespace(self, node):
        ''' Strip out the "{amqp namespace}" ahead of each tag'''
        pos = node.tag.find("}")
        if pos > 0:
            node.tag = node.tag[pos+1:]
        for child in node:
            self.trimNamespace(child)

xmlTypes        = XmlStore("codec" + os.sep + "types.xml")
xmlTransport    = XmlStore("transport.xml")
xmlMessaging    = XmlStore("messaging.xml")
xmlSecurity     = XmlStore("security.xml")
xmlTransactions = XmlStore("transactions.xml")

#
# Utilities
#
#
class ExitStatus(Exception):
    """Raised if a command wants a non-0 exit status from the script"""
    def __init__(self, status): self.status = status

def nbsp():
    return "&#160;"

def lozenge():
    return "&#9674;"

def double_lozenge():
    return lozenge() + lozenge()

#
# Open html page header
def print_fixed_leading():
    # start up the web stuff
    print ("<html>")
    print ("<head>")
    print ("<title>AMQP 1.0 - Interactive Protocol Spec</title>")
    print ('''<script src="http://ajax.googleapis.com/ajax/libs/dojo/1.4/dojo/dojo.xd.js" type="text/javascript"></script>
<!-- <script src="http://ajax.googleapis.com/ajax/libs/dojo/1.4/dojo/dojo.xd.js" type="text/javascript"></script> -->
<script type="text/javascript">
function node_is_visible(node)
{
  if(dojo.isString(node))
    node = dojo.byId(node);
  if(!node) 
    return false;
  return node.style.display == "block";
}
function set_node(node, str)
{
  if(dojo.isString(node))
    node = dojo.byId(node);
  if(!node) return;
  node.style.display = str;
}
function toggle_node(node)
{
  if(dojo.isString(node))
    node = dojo.byId(node);
  if(!node) return;
  set_node(node, (node_is_visible(node)) ? 'none' : 'block');
}
function hide_node(node)
{
  set_node(node, 'none');
}
function show_node(node)
{
  set_node(node, 'block');
}

function go_back()
{
  window.history.back();
}
''')


#
#
def print_start_body():
    print ("</script>")
    print ("</head>")
    print ("<body>")
    print ("<style>")
    print ("    * { font-family: sans-serif; }")
    print ("</style>")
    print ("<style>")
    print ("table, th, td {")
    print ("  border: 1px solid black;")
    print ("  border-collapse: collapse;")
    print ("}")
    print ("th, td {")
    print ("  padding: 4px;")
    print ("}")
    print ("</style>")

#
#
def print_toc():
    # Table of Contents
    print("<a href=\"#Types\">Types</a><br>")
    print("%s%s<a href=\"#PrimitiveTypes\">Primitive Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#DescribedTypes\">Described Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#RestrictedTypes\">Restricted Types - Enumerations</a><br>" % (nbsp(), nbsp()))
    print("<hr>")


#
#
encoding_typenames = []
encoding_codes = []
encoding_typemap = {}
encoding_codemap = {}

def compute_primitive_types():
    # create sorted lists for display
    for type in typesPrimitive:
        for enc in type:
            typename = type.get("name")
            if enc.get("name") is not None:
                typename += ":" + enc.get("name")
            typecode = enc.get("code")
            enc.text = typename
            if not typename in encoding_typenames:
                encoding_typenames.append(typename)
                encoding_codes.append(typecode)
                encoding_typemap[typename] = enc
                encoding_codemap[typecode] = enc
            else:
                raise ValueError("duplicate encoding type name: '%s'" % typename)
    encoding_typenames.sort()
    encoding_codes.sort()

def print_primitive_types():
    # print types sorted by class name
    print("<h4>Primitive Types</h4>")
    print("<a name=\"PrimitiveTypes\"></a>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sby Name<br>" % ("PrimTypeName", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"PrimTypeName\">")
    print("<table>")
    print("<tr>")
    print(" <th>Name</th>")
    print(" <th>Code</th>")
    print(" <th>Category</th>")
    print(" <th>Width</th>")
    print("</tr>")
    for typen in encoding_typenames:
        enc = encoding_typemap[typen]
        print("<tr>")
        print(" <td>%s</td>" % enc.text)
        print(" <td>%s</td>" % enc.get("code"))
        print(" <td>%s</td>" % enc.get("category"))
        print(" <td>%s</td>" % enc.get("width"))
        print("</tr>")
    print("</table>")
    print("</div>")

    # print types sorted by class code
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sby Code<br>" % ("PrimTypeCode", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"PrimTypeCode\">")
    print("<table>")
    print("<tr>")
    print(" <th>Name</th>")
    print(" <th>Code</th>")
    print(" <th>Category</th>")
    print(" <th>Width</th>")
    print("</tr>")
    for code in encoding_codes:
        enc = encoding_codemap[code]
        print("<tr>")
        print(" <td>%s</td>" % enc.text)
        print(" <td>%s</td>" % enc.get("code"))
        print(" <td>%s</td>" % enc.get("category"))
        print(" <td>%s</td>" % enc.get("width"))
        print("</tr>")
    print("</table>")
    print("</div>")


#
#
def print_end_body():
    print ("</body>")
    print ("</html>")


#
#
def main_except(argv):
    # Compute tables and stuff that may be needed by show/hide functions
    compute_primitive_types()

    # Print the web page
    print_fixed_leading()
    # TODO: insert show/hide functions into web page header
    print_start_body()

    # Hello World!
    print("Rolke's proof of concept AMQP-spec-as-web-page.<br>This is autogenerated from the same source xml used by proton-c.<br>With approval this can be added to the proton-c build scheme and generated each time you execute make!<br>")

    print("<h1>AMQP 1.0 - Interactive Protocol Spec</h1>")

    print_toc()
    print_primitive_types()
    print_end_body()


#
#
def main(argv):
    try:
        main_except(argv)
        return 0
    except ExitStatus, e:
        return e.status
    except Exception, e:
        print("%s: %s"%(type(e).__name__, e))
        return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
