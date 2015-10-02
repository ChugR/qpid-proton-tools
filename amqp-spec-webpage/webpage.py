#!/usr/bin/env python
#
# Version 0.3
# Original work by Chuck Rolke

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
# Originally this was to run in the proton-c source area but those
# xml files had the label fields stripped. The label fields add a lot
# to the result and so the source spec xml was hacked yet again for
# this work.

# The page layout generally follows the layout of the AMQP 1.0 spec.
#
# TODO: scavenge the ascii art from <doc> sections
# TODO: this code generates index data while printing table data.
#       clean this up.
#

from __future__ import print_function
import sys, optparse, os, time
import xml.etree.ElementTree as ET

#
#
def log(text):
    print("LOG: ", text, file=sys.stderr)


#
# construct data stores
typesPrimitive = []  # class == primitive
typesEnumerated = [] # no descriptor, choice count > 0
typesRestricted = [] # no descriptor, choice count == 0
typesDescribed = []  # contains descriptor

typesAll = {}    # table[typename] = typenode for clean types

#
# indices computed while generating page
typeNameIndex = []
typeIndex = {}     # key='name', value = [list of types]

fieldNameIndex = []
fieldIndex = {}

enumNameIndex = [] # names of enum values (not types)
enumIndex = {}

grandNameIndex = []
grandIndex = {}

xrefNameIndex = []
xrefIndex = {}

#
# provided types indexed by name of provided type, value is list of provider types
providedtypenames = []
provided = {} # {'name' : [type, type] with provides=name

#
# definition objects are constants
definitionsAll = []

#
# stats
class Stats():
    def __init__(self):
        self.nConstants = 0
        self.nPrimitiveEncodings = 0
        self.nEnumeratedTypes = 0
        self.nRestrictedTypes = 0
        self.nDescribedTypes = 0
        self.nProvidedTypes = 0
        self.nIndexedTypes = 0
        self.nIndexedFields = 0
        self.nIndexedEnumerations = 0
        self.nIndexedGrand = 0
        self.nIndexedXrefs = 0

    def log(self):
        log("STAT: nConstants           = %s" % self.nConstants)
        log("STAT: nPrimitiveEncodings  = %s" % self.nPrimitiveEncodings)
        log("STAT: nEnumeratedTypes     = %s" % self.nEnumeratedTypes)
        log("STAT: nRestrictedTypes     = %s" % self.nRestrictedTypes)
        log("STAT: nDescribedTypes      = %s" % self.nDescribedTypes)
        log("STAT: nProvidedTypes       = %s" % self.nProvidedTypes)
        log("STAT: nIndexedTypes        = %s" % self.nIndexedTypes)
        log("STAT: nIndexedFields       = %s" % self.nIndexedFields)
        log("STAT: nIndexedEnumerations = %s" % self.nIndexedEnumerations)
        log("STAT: nIndexedGrand        = %s" % self.nIndexedGrand)
        log("STAT: nIndexedXrefs        = %s" % self.nIndexedXrefs)

    def statCheck(self, name, expectedValue):
        currentValue = getattr(self, name)
        if not currentValue == expectedValue:
            log("WARNING stat %s expected %s but is actaully %s" % (name, expectedValue, currentValue))

stats = Stats()

class XmlStore():
    def __init__(self, filename):
        self.filename = filename
        self.tree = ET.parse(os.path.join(os.path.dirname(__file__), filename))
        self.root = self.tree.getroot()  # root=Element 'amqp'
        self.trimNamespace(self.root)
        self.rootName = self.root.get("name")
        self.sections = self.root.findall("section")
        self.types = []
        self.definitions = []
        for section in self.sections:
            ltypes = section.findall("type")
            for type in ltypes:
                # decorate and categorize each type
                typesAll[type.get("name")] = type
                type.text = self.rootName + ":" + section.get("name")
                if type.get("class") == "primitive":
                    typesPrimitive.append(type)
                else:
                    descr = type.find("descriptor")
                    if descr is None:
                        choices = type.find("choice")
                        if choices is None:
                            typesRestricted.append(type)
                        else:
                            typesEnumerated.append(type)                            
                    else:
                        typesDescribed.append(type)
                provides = type.get("provides")
                if provides is not None and not provides == "":
                    providelist = provides.replace(' ','').split(',')
                    for p in providelist:
                        if not p in provided:
                            providedtypenames.append(p)
                            provided[p] = []
                        provided[p].append(type)
            self.types += section.findall("type")
            ldefs = section.findall("definition")
            for definition in ldefs:
                #log("definition %s" % definition.get("name"))
                definition.text = self.rootName + ":" + section.get("name")
                definitionsAll.append(definition)
            self.definitions += section.findall("definition")
        
    def trimNamespace(self, node):
        ''' Strip out the "{amqp namespace}" ahead of each tag'''
        pos = node.tag.find("}")
        if pos > 0:
            node.tag = node.tag[pos+1:]
        for child in node:
            self.trimNamespace(child)

xmlTypes        = XmlStore("types.xml")
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

def extract_descr_type_code(code):
    return "0x" + code[19:]

def noNoneString(str):
    if str:
        return str
    return ""

def noNoneTypeRef(str):
    if str and not str == "":
        res = "<a href=\"#TYPE_%s\">%s</a>" % (str, str)
        return res
    return ""

def noNoneProvideRef(str):
    if str and not str == "":
        res = ""
        mylist = str.replace(' ','').split(',')
        for e in mylist:
            res += "<a href=\"#PROVIDEDTYPE_%s\">%s</a> " % (e, e)
        return res
    return ""

def addToIndex(name, section):
    if not name in typeNameIndex:
        typeNameIndex.append(name)
        typeIndex[name] = []
    typeIndex[name].append(section)

def addToFieldIndex(name, parentsection, parenttype):
    if not name in fieldNameIndex:
        fieldNameIndex.append(name)
        fieldIndex[name] = []
    fieldIndex[name].append( [parentsection, parenttype] )

def addToEnumIndex(name, parentsection, parenttype):
    if not name in enumNameIndex:
        enumNameIndex.append(name)
        enumIndex[name] = []
    enumIndex[name].append( [parentsection, parenttype] )

def addToGrandIndex(name, decoratedname, category, psect, ptype):
    if not name in grandNameIndex:
        grandNameIndex.append(name)
        grandIndex[name] = []
    grandIndex[name].append( [decoratedname, category, psect, ptype] )

def addToXrefIndex(name, decReferrerName, category, referrerSection):
    if not name in xrefNameIndex:
        xrefNameIndex.append(name)
        xrefIndex[name] = []
    xrefIndex[name].append( [decReferrerName, category, referrerSection] )

#
# Open html page header
def print_fixed_leading():
    # start up the web stuff
    print ("<html>")
    print ("<head>")
    print ("<title>AMQP 1.0 - Interactive Protocol Spec</title>")
    print ('''<script src="http://ajax.googleapis.com/ajax/libs/dojo/1.4/dojo/dojo.xd.js" type="text/javascript"></script>
<!-- <script src="http://ajax.googleapis.com/ajax/libs/dojo/1.4/dojo/dojo.xd.js" type="text/javascript"></script> -->
<!--
 -
 - Licensed to the Apache Software Foundation (ASF) under one
 - or more contributor license agreements.  See the NOTICE file
 - distributed with this work for additional information
 - regarding copyright ownership.  The ASF licenses this file
 - to you under the Apache License, Version 2.0 (the
 - "License"); you may not use this file except in compliance
 - with the License.  You may obtain a copy of the License at
 -
 -   http://www.apache.org/licenses/LICENSE-2.0
 -
 - Unless required by applicable law or agreed to in writing,
 - software distributed under the License is distributed on an
 - "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 - KIND, either express or implied.  See the License for the
 - specific language governing permissions and limitations
 - under the License.
 -
-->
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
    print("function show_all_tables()")
    print("{")
    print("  show_node('Constants');")
    print("  show_node('PrimTypeName');")
    print("  show_node('DescrTypes');")
    print("  show_node('EnumTypes');")
    print("  show_node('RestrTypes');")
    print("  show_node('ProvTypes');")
    print("  show_node('TypIndex');")
    print("  show_node('FldIndex');")
    print("  show_node('EnuIndex');")
    print("  show_node('GndIndex');")
    print("  show_node('XrefIndex');")
    for type in typesDescribed:
        print("  show_node('DT%s')" % type.get("name"))
    for type in typesEnumerated:
        print("  show_node('ET%s')" % type.get("name"))
    print("}")
    print("")
    print("function hide_all_tables()")
    print("{")
    print("  hide_node('Constants');")
    print("  hide_node('PrimTypeName');")
    print("  hide_node('DescrTypes');")
    print("  hide_node('EnumTypes');")
    print("  hide_node('RestrTypes');")
    print("  hide_node('ProvTypes');")
    print("  hide_node('TypIndex');")
    print("  hide_node('FldIndex');")
    print("  hide_node('EnuIndex');")
    print("  hide_node('GndIndex');")
    print("  hide_node('XrefIndex');")
    for type in typesDescribed:
        print("  show_node('DT%s')" % type.get("name"))
    for type in typesEnumerated:
        print("  show_node('ET%s')" % type.get("name"))
    print("}")

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
    print("<a href=\"#Constants\">Constants</a><br>")
    print("<a href=\"#Types\">Types</a><br>")
    print("%s%s<a href=\"#PrimitiveTypes\">Primitive Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#EnumeratedTypes\">Enumerated Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#RestrictedTypes\">Restricted Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#DescribedTypes\">Described Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#ProvidedTypes\">Provided Types</a><br>" % (nbsp(), nbsp()))
    print("<a href=\"#Indices\">Indices</a><br>")
    print("%s%s<a href=\"#TypeIndex\">Types</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#FieldIndex\">Fields</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#EnumerationIndex\">Enumerations</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#GrandIndex\">Grand Index</a><br>" % (nbsp(), nbsp()))
    print("%s%s<a href=\"#XrefIndex3\">Type Cross Reference</a><br>" % (nbsp(), nbsp()))

    print("<hr>")
    print("<strong>NOTE: Tables must be expanded or internal hyperlinks don't work.</strong><br>")
    print("<a href=\"javascript:show_all_tables()\"> %s </a>%sTable view: expand all.<br>" % (lozenge(), nbsp()))
    print("<a href=\"javascript:hide_all_tables()\"> %s </a>%sTable view: collapse all." % (lozenge(), nbsp()))
    print("<hr>")


def print_constants():
    # print types sorted by class name
    print("<a name=\"Constants\"></a>")
    print("<h2>Constants</h2>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sConstants<br>" % ("Constants", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"Constants\">")
    print("<table>")
    print("<tr>")
    print(" <th>Section</th>")
    print(" <th>Name</th>")
    print(" <th>Value</th>")
    print(" <th>Label</th>")
    print("</tr>")
    for definition in definitionsAll:
        print("<tr>")
        print(" <td>%s</td>" % definition.text)
        print(" <td><a name=\"TYPE_%s\"></a><strong>%s</strong></td>" % (definition.get("name"),definition.get("name")))
        print(" <td>%s</td>" % definition.get("value"))
        print(" <td>%s</td>" % definition.get("label"))
        print("</tr>")
        addToIndex(definition.get("name"), definition.text) # Constants
        stats.nConstants += 1
    print("</table>")
    print("</div>")
    print("<br>")


#
#
encoding_typenames = []
encoding_codes = []
encoding_typemap = {}
encoding_codemap = {}
encoding_sectionmap = {}

def compute_primitive_types():
    # create sorted lists for display
    for type in typesPrimitive:
        for enc in type.findall("encoding"):
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
                encoding_sectionmap[typename] = type.text
            else:
                raise ValueError("duplicate encoding type name: '%s'" % typename)
    encoding_typenames.sort()
    encoding_codes.sort()

def print_primitive_types():
    # print types sorted by class name
    print("<a name=\"Types\"></a>")
    print("<h2>Types</h2>")
    print("<a name=\"PrimitiveTypes\"></a>")
    print("<h3>Primitive Types</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sby Name<br>" % ("PrimTypeName", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"PrimTypeName\">")
    print("<table>")
    print("<tr>")
    print(" <th>Section</th>")
    print(" <th>Name</th>")
    print(" <th>Code</th>")
    print(" <th>Category</th>")
    print(" <th>Width</th>")
    print(" <th>Label</th>")
    print("</tr>")
    for type in typesPrimitive:
        print("<tr>")
        print(" <td>%s</td>" % type.text)
        print(" <td><a name=\"TYPE_%s\"></a><strong>%s</strong></td>" % (type.get("name"), type.get("name")))
        print(" <td></td>")
        print(" <td></td>")
        print(" <td></td>")
        print(" <td>%s</td>" % type.get("label"))
        print("</tr>")
        addToIndex(type.get("name"), type.text) # Primitive category
        for enc in type.findall("encoding"):
            print("<tr>")
            print(" <td></td>")
            print(" <td><a name=\"TYPE_%s\"></a><strong>%s</strong></td>" % (enc.text, enc.text))
            print(" <td>%s</td>" % enc.get("code"))
            print(" <td>%s</td>" % enc.get("category"))
            print(" <td>%s</td>" % enc.get("width"))
            print(" <td>%s</td>" % enc.get("label"))
            print("</tr>")
            addToIndex(enc.text, "types:encodings") # Primitive type
            stats.nPrimitiveEncodings += 1
    # Phony primitive type "*"
    print("<tr>")
    print(" <td>spec:wildcard</td>")
    print(" <td><a name=\"TYPE_*\"><strong>*</strong></a></td>")
    print(" <td></td>")
    print(" <td></td>")
    print(" <td></td>")
    print(" <td>A value of any type is permitted.</td>")
    print("</tr>")
    print("</table>")
    print("</div>")
    print("<br>")

    # print types sorted by class code
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sby Code<br>" % ("PrimTypeCode", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"PrimTypeCode\">")
    print("<table>")
    print("<tr>")
    print(" <th>Section</th>")
    print(" <th>Name</th>")
    print(" <th>Code</th>")
    print(" <th>Category</th>")
    print(" <th>Width</th>")
    print(" <th>Label</th>")
    print("</tr>")
    for code in encoding_codes:
        enc = encoding_codemap[code]
        print("<tr>")
        print(" <td>%s</td>" % "types:encodings")
        print(" <td><strong>%s</strong></td>" % enc.text)
        print(" <td>%s</td>" % enc.get("code"))
        print(" <td>%s</td>" % enc.get("category"))
        print(" <td>%s</td>" % enc.get("width"))
        print(" <td>%s</td>" % enc.get("label"))
        print("</tr>")
    print("</table>")
    print("</div>")
    print("<br>")


#
#
descr_longnames = []   # "transport:performatives open"
descr_codes = []       # "0x10"
descr_codemap = {}     # map[longname] = "0x10"
descr_mapcode = {}     # map[code] = longname
descr_typemap = {}     # map[longname] = type node
descr_fieldmap = {}    # map[longname] = [list-of-field-nodes]
descr_fieldindex = []  # list of (fieldname, field's_parent_type_node)
# TODO: get the provides info
def compute_described_types():
    for type in typesDescribed:
        descriptor = type.find("descriptor")
        descr_name = descriptor.get("name")
        descr_code = extract_descr_type_code(descriptor.get("code"))
        fields = type.findall("field")
        longname = type.text + " " + type.get("name")
        descr_longnames.append(longname)
        descr_codes.append(descr_code)
        descr_codemap[longname] = descr_code
        descr_mapcode[descr_code] = longname
        descr_typemap[longname] = type
        if fields is not None:
            descr_fieldmap[longname] = fields
            for field in fields:
                descr_fieldindex.append( (field.get("name"), type) )
    descr_codes.sort()


#
#
def print_described_types():
    print("<a name=\"DescribedTypes\"></a>")
    print("<h3>Described Types</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sDescribed Types<br>" % ("DescrTypes", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"DescrTypes\">")
    print("<table>")
    print("<tr>")
    print(" <th>Section</th>")
    print(" <th>Name</th>")
    print(" <th>Code</th>")
    print(" <th>Type</th>")
    print(" <th>Provides</th>")
    print(" <th>Label</th>")
    print("</tr>")
    for code in descr_codes:
        name = descr_mapcode[code]
        descr_key = name.split()
        section = descr_key[0]
        descr_typename = descr_key[1]
        type = descr_typemap[name]
        print("<tr id=\"TYPE_%s\">" % descr_typename)
        print(" <td>%s</td>" % section)
        print(" <td><a href=\"#details_%s\"><strong>%s</strong></a></td>" % (descr_typename, descr_typename))
        print(" <td>%s</td>" % code)
        print(" <td><a href=\"#TYPE_%s\">%s</a></td>" % (type.get("source"), type.get("source")))
        print(" <td>%s</td>" % noNoneProvideRef(type.get("provides")))
        print(" <td>%s</td>" % noNoneString(type.get("label")))
        print("</tr>")
        addToIndex(descr_typename, section) # Described
        stats.nDescribedTypes += 1
    print("</table>")
    print("<br>")

    for code in descr_codes:
        name = descr_mapcode[code]
        descr_key = name.split()
        section = descr_key[0]
        descr_typename = descr_key[1]
        type = descr_typemap[name]
        print("<a name=\"details_%s\"></a>" % descr_typename)
        print("%s%s<a href=\"javascript:toggle_node('%s')\"> %s </a>%s %s<strong><a href=\"#TYPE_%s\">%s</a></strong><br>" % \
              (nbsp(), nbsp(), "DT"+descr_typename, lozenge(), nbsp(), "Described type: " + section + " - ", descr_typename, descr_typename))
        print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"%s\">" % ("DT"+descr_typename))
        print("<table>")
        print("<tr>")
        print(" <th>Tag</th>")
        print(" <th>Name</th>")
        print(" <th>Type</th>")
        print(" <th>Requires</th>")
        print(" <th>Default</th>")
        print(" <th>Mandatory</th>")
        print(" <th>Multiple</th>")
        print(" <th>Label</th>")
        print("</tr>")
        for child in type:
            childtag = ""
            childtype = ""
            printthis = True
            if child.tag == "field":
                childtype = child.get("type")
                childlabel = noNoneString(child.get("label"))
                childname ="<a id=\"FIELD_%s_%s\">%s</a>" % (descr_typename, child.get("name"), child.tag)
                childtag = " <td>%s</td>" % (childname)
                addToFieldIndex(child.get("name"), section, descr_typename)
            elif child.tag == "descriptor":
                childlabel = noNoneString(type.get("label"))
                childtag = " <td>%s</td>" % child.tag
            else:
                printthis = False
            if printthis:
                print("<tr>")
                print("%s" % childtag)
                print(" <td><strong>%s</strong></td>" % child.get("name"))
                print(" <td><a href=\"#TYPE_%s\">%s</a></td>" % (childtype, childtype))
                print(" <td>%s</td>" % noNoneProvideRef(child.get("requires")))
                print(" <td>%s</td>" % noNoneString(child.get("default")))
                print(" <td>%s</td>" % noNoneString(child.get("mandatory")))
                print(" <td>%s</td>" % noNoneString(child.get("multiple")))
                print(" <td>%s</td>" % childlabel)
                print("</tr>")
        print("</table>")
        print("<br>")
        print("</div>")  # End one described type
   
    print("</div>")   # End described type details
    print("<br>")


#
#
enum_longnames = []    # "messaging:message-format terminus-durability"
enum_typemap = {}      # map[longname] = type node
enum_choicemap = {}    # map[longname] = [list-of-choice-fields]
enum_choiceindex = {}  # list of (choicename, choice's_parent_type_node)

def compute_enumerated_types():
    #log("typesEnumerated: %s" % typesEnumerated)
    for type in typesEnumerated:
        #log("processing enum %s" % type.get("name"))
        longname = type.text + " " + type.get("name")
        enum_longnames.append(longname)
        enum_typemap[longname] = type
        #        if choices is not None:
        #            enum_choicemap[longname] = choices
        #            for choice in choices:
        #                log("processing enum choice %s" % choice.get("name"))
        #                enum_choiceindex.append( (choice.get("name"), type) )
        choices = []
        for child in type:
            if child.tag == "choice":
                choices += child
                enum_choiceindex[child.get("name")] = type
                addToEnumIndex(child.get("name"), type.text, type.get("name"))
        enum_choicemap[longname] = choices
    enum_longnames.sort()
        
def print_enumerated_types():
    print("<a name=\"EnumeratedTypes\"></a>")
    print("<h3>Enumerated Types</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sEnumerated Types<br>" % ("EnumTypes", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"EnumTypes\">")
    print("<table>")
    print("<tr>")
    print(" <th>Section</th>")
    print(" <th>Name</th>")
    print(" <th>Type</th>")
    print(" <th>Label</th>")
    print(" <th>Provides</th>")
    print("</tr>")
    for lname in enum_longnames:
        type = enum_typemap[lname]
        print("<tr id=\"TYPE_%s\">" % type.get("name"))
        print(" <td>%s</td>" % type.text)
        print(" <td><a href=\"#details_%s\"><strong>%s</strong></a></td>" % (type.get("name"), type.get("name")))
        print(" <td><a href=\"#TYPE_%s\">%s</a></td>" % (type.get("source"), type.get("source")))
        print(" <td>%s</td>" % noNoneString(type.get("label")))
        print(" <td>%s</td>" % noNoneProvideRef(type.get("provides")))
        print("</tr>")
        addToIndex(type.get("name"), type.text) # Enum
        stats.nEnumeratedTypes += 1
    print("</table>")
    print("<br>")

    for lname in enum_longnames:
        type = enum_typemap[lname]
        enum_key = lname.split()
        section = enum_key[0]
        enum_typename = enum_key[1]
        print("<a name=\"details_%s\"></a>" % (enum_typename))
        print("%s%s<a href=\"javascript:toggle_node('%s')\"> %s </a>%s %s<strong><a href=\"#TYPE_%s\">%s</a></strong><br>" % \
              (nbsp(), nbsp(), "ET"+enum_typename, lozenge(), nbsp(), "Enumerated type: " + section + " - ", enum_typename, enum_typename))
        print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"%s\">" % ("ET"+enum_typename))
        print("<table>")
        print("<tr>")
        print(" <th>Name</th>")
        print(" <th>Type/Value</th>")
        print(" <th>Label</th>")
        print(" <th>Provides</th>")
        print("</tr>")
        print("<tr>")
        print(" <td><strong>%s</strong></td>" % (type.get("name")))
        print(" <td><a href=\"#TYPE_%s\">%s</a></td>" % (type.get("source"), type.get("source")))
        print(" <td>%s</td>" % noNoneString(type.get("label")))
        print(" <td>%s</td>" % noNoneProvideRef(type.get("provides")))
        print("</tr>")
        for child in type.findall("choice"):
            print("<tr>")
            print(" <td><strong>%s</strong></td>" % child.get("name"))
            print(" <td>%s</td>" % child.get("value"))
            print("</tr>")
        print("</table>")
        print("<br>")
        print("</div>")
    print("</div>")   # End enumerated type details
    print("<br>")

#
#
def print_restricted_types():
    print("<a name=\"RestrictedTypes\"></a>")
    print("<h3>Restricted Types</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sRestricted Types<br>" % ("RestrTypes", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"RestrTypes\">")
    print("<table>")
    print("<tr>")
    print(" <th>Section</th>")
    print(" <th>Name</th>")
    print(" <th>Type</th>")
    print(" <th>Label</th>")
    print(" <th>Provides</th>")
    print("</tr>")
    for type in typesRestricted:
        print("<tr>")
        print(" <td>%s</td>" % type.text)
        print(" <td><strong><a name=\"TYPE_%s\">%s</a></strong></td>" % (type.get("name"), type.get("name")))
        print(" <td><a href=\"#TYPE_%s\">%s</a></td>" % (type.get("source"),type.get("source")))
        print(" <td>%s</td>" % noNoneString(type.get("label")))
        print(" <td>%s</td>" % noNoneProvideRef(type.get("provides")))
        print("</tr>")
        addToIndex(type.get("name"), type.text) # Restricted
        stats.nRestrictedTypes += 1
    print("</table>")
    print("</div>")
    print("<br>")


#
#
def print_provided_types():
    providedtypenames.sort()
    print("<a name=\"ProvidedTypes\"></a>")
    print("<h3>Provided Types</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sProvided Types<br>" % ("ProvTypes", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"ProvTypes\">")
    print("<table>")
    print("<tr>")
    print(" <th>Provided Type</th>")
    print(" <th>Provider</th>")
    print(" <th>Provider Section</th>")
    print("</tr>")
    for ptype in providedtypenames:
        anchor = " id=\"PROVIDEDTYPE_%s\"" % ptype
        types = provided[ptype]
        addToIndex(ptype, "PROVIDED")
        stats.nProvidedTypes += 1
        for type in types:
            print("<tr%s>" % anchor)
            anchor = ""
            print(" <td>%s</td>" % ptype)
            print(" <td>%s</td>" % noNoneTypeRef(type.get("name")))
            print(" <td>%s</td>" % type.text)
            print("</tr>")
    print("</table>")
    print("</div>")
    print("<br>")
        
#
#
def print_type_index():
    typeNameIndex.sort()
    print("<a name=\"Indices\"></a>")
    print("<h2>Indices</h2>")
    print("<a name=\"TypeIndex\"></a>")
    print("<h3>Type Index</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sType Index<br>" % ("TypIndex", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"TypIndex\">")
    print("<table>")
    print("<tr>")
    print(" <th>Type Name</th>")
    print(" <th>Section</th>")
    print("</tr>")
    for idx in typeNameIndex:
        sections = typeIndex[idx]
        for section in sections:
            print("<tr>")
            if section == "PROVIDED":
                name = noNoneProvideRef(idx)
            else:
                name = noNoneTypeRef(idx)
            print(" <td>%s</td>" % name)
            print(" <td>%s</td>" % section)
            print("</tr>")
            addToGrandIndex(idx, name, "type", section, " ")
            stats.nIndexedTypes += 1
    print("</table>")
    print("</div>")
    print("<br>")
        

#
#
def print_field_index():
    fieldNameIndex.sort()
    print("<a name=\"FieldIndex\"></a>")
    print("<h3>Field Index</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sField Index<br>" % ("FldIndex", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"FldIndex\">")
    print("<table>")
    print("<tr>")
    print(" <th>Field Name</th>")
    print(" <th>Parent Type</th>")
    print(" <th>Section</th>")
    print("</tr>")
    for idx in fieldNameIndex:
        parents = fieldIndex[idx]
        for parent in parents:
            psect = parent[0]
            ptype = parent[1]
            print("<tr>")
            name = "<a href=\"#FIELD_%s_%s\">%s</a>" % (ptype, idx, idx)
            print(" <td>%s</td>" % name)
            print(" <td>%s</td>" % ptype)
            print(" <td>%s</td>" % psect)
            print("</tr>")
            addToGrandIndex(idx, name, "field", psect, ptype)
            stats.nIndexedFields += 1
    print("</table>")
    print("</div>")
    print("<br>")


#
#
def print_enumeration_index():
    enumNameIndex.sort()
    print("<a name=\"EnumerationIndex\"></a>")
    print("<h3>Enumeration Index</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sEnumeration Index<br>" % ("EnuIndex", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"EnuIndex\">")
    print("<table>")
    print("<tr>")
    print(" <th>Enum Value</th>")
    print(" <th>Enumeration</th>")
    print(" <th>Section</th>")
    print("</tr>")
    for idx in enumNameIndex:
        parents = enumIndex[idx]
        for parent in parents:
            psect = parent[0]
            ptype = parent[1]
            enum = "<a href=\"#TYPE_%s\">%s</a>" % (ptype, ptype)
            print("<tr>")
            print(" <td>%s</td>" % idx)
            print(" <td>%s</td>" % enum)
            print(" <td>%s</td>" % psect)
            print("</tr>")
            addToGrandIndex(idx, idx, "enum value", psect, enum)
            stats.nIndexedEnumerations += 1
    print("</table>")
    print("</div>")
    print("<br>")


#
#
def print_grand_index():
    grandNameIndex.sort()
    print("<a name=\"GrandIndex\"></a>")
    print("<h3>Grand Index</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sGrand Index<br>" % ("GndIndex", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"GndIndex\">")
    print("<table>")
    print("<tr>")
    print(" <th>Name</th>")
    print(" <th>Category</th>")
    print(" <th>Parent</th>")
    print(" <th>Section</th>")
    print("</tr>")
    for idx in grandNameIndex:
        parents = grandIndex[idx]
        for parent in parents:
            print("<tr>")
            print(" <td>%s</td>" % parent[0])
            print(" <td>%s</td>" % parent[1])
            print(" <td>%s</td>" % parent[2])
            print(" <td>%s</td>" % parent[3])
            print("</tr>")
            stats.nIndexedGrand += 1
    print("</table>")
    print("</div>")
    print("<br>")


#
#
def print_xref_index():
    #     Create xref name index from type index.
    xrefNameIndex.append("*")
    for idx in typeNameIndex:
        sections = typeIndex[idx]
        for section in sections:
            name = idx
            if section == "PROVIDED":
                name += ",PROVIDED"
            if name not in xrefNameIndex:
                xrefNameIndex.append(name)
            else:
                # primitive type names get reused as encoding names...
                pass
        
    xrefNameIndex.sort()
    for name in xrefNameIndex:
        xrefIndex[name] = [] # list of types defined in terms of type 'name'

    # Enum types
    for lname in enum_longnames:
        type = enum_typemap[lname]
        decname = noNoneTypeRef(type.get("name"))
        source = type.get("source")
        category = "enum"
        refSection = type.text
        xrefIndex[source].append( [decname, category, refSection])

    # Restricted types
    for type in typesRestricted:
        decname = noNoneTypeRef(type.get("name"))
        source = type.get("source")
        category = "restricted"
        refSection = type.text
        xrefIndex[source].append( [decname, category, refSection])

    # Described types
    for code in descr_codes:
        name = descr_mapcode[code]
        descr_key = name.split()
        section = descr_key[0]
        descr_typename = descr_key[1]
        type = descr_typemap[name]
        decname = noNoneTypeRef(descr_typename)
        source = type.get("source")
        category = "described"
        refSection = section
        xrefIndex[source].append( [decname, category, refSection])

    # Described fields
    for code in descr_codes:
        name = descr_mapcode[code]
        descr_key = name.split()
        section = descr_key[0]
        descr_typename = descr_key[1]
        type = descr_typemap[name]
        for child in type:
            if child.tag == "field":
                decname = "<a href=\"#FIELD_%s_%s\">%s</a>" % (descr_typename, child.get("name"), child.get("name"))
                source = child.get("type")
                category = "field"
                refSection = "%s - %s" % (section, descr_typename)
                xrefIndex[source].append( [decname, category, refSection])

    # Provided types
    for ptype in providedtypenames:
        types = provided[ptype]
        for type in types:
            decname = noNoneTypeRef(type.get("name"))
            source = "%s,%s" % (ptype, "PROVIDED")
            category = "provided"
            refSection = ""
            xrefIndex[source].append( [decname, category, refSection])
    print("<a name=\"XrefIndex3\"></a>")
    print("<h3>Cross Reference Index</h3>")
    print("<a href=\"javascript:toggle_node('%s')\"> %s </a>%sType Cross Reference<br>" % ("XrefIndex", lozenge(), nbsp()))
    print("<div width=\"100%%\" style=\"display:none\"  margin-bottom:\"2px\" id=\"XrefIndex\">")
    print("<table>")
    print("<tr>")
    print(" <th>Referenced Type</th>")
    print(" <th>Referrer</th>")
    print(" <th>Section</th>")
    print(" <th>Type</th>")
    print("</tr>")
    for idx in xrefNameIndex:
        if ":" not in idx:
            try:
                idxlist = idx.split(',')
                typetext = ""
                typename = ""
                if len(idxlist) == 1:
                    if idx == "*":
                        typetext = "spec:wildcard"
                        typename = "*"
                    else:
                        type = typesAll[idx]
                        typetext = type.text
                        typename = idxlist[0]
                else:
                    typetext = "provided"
                    typename = "<a href=\"#PROVIDEDTYPE_%s\"> %s </a>" % (idxlist[0], idxlist[0])
                refs = xrefIndex[idx]
                if len(refs) == 0:
                    print("<tr>")
                    print(" <td>%s:<strong>%s</strong></td>" % (typetext, typename))
                    print(" <td>%s</td>" % nbsp())
                    print(" <td>%s</td>" % nbsp())
                    print(" <td>%s</td>" % nbsp())
                    print("</tr>")
                for ref in refs:
                    print("<tr>")
                    print(" <td>%s:<strong>%s</strong></td>" % (typetext, typename))
                    print(" <td>%s</td>" % ref[0])
                    print(" <td>%s</td>" % ref[2])
                    print(" <td>%s</td>" % ref[1])
                    print("</tr>")
                    stats.nIndexedXrefs += 1
            except:
                #log("Can't resolve as type: %s" % idx) # constants can't be resolved
                pass
    print("</table>")
    print("</div>")
    print("<br>")


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
    compute_described_types()
    compute_enumerated_types()
    
    # Print the web page
    print_fixed_leading()
    print_start_body()

    print("<h1>AMQP 1.0 - Interactive Protocol Type Reference</h1>")

    print_toc()
    print_constants()
    print_primitive_types()
    print_enumerated_types()
    print_restricted_types()
    print_described_types()
    print_provided_types()
    print_type_index()
    print_field_index()
    print_enumeration_index()
    print_grand_index()
    print_xref_index()
    
    print_end_body()

    stats.statCheck("nConstants", 13)
    stats.statCheck("nPrimitiveEncodings", 39)
    stats.statCheck("nEnumeratedTypes", 13)
    stats.statCheck("nRestrictedTypes", 19)
    stats.statCheck("nDescribedTypes", 40)
    stats.statCheck("nProvidedTypes", 14)
    stats.statCheck("nIndexedTypes", 162)
    stats.statCheck("nIndexedFields", 125)
    stats.statCheck("nIndexedEnumerations", 54)
    stats.statCheck("nIndexedGrand", 341)
    stats.statCheck("nIndexedXrefs", 252)

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
