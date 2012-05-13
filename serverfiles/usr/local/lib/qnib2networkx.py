#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of QNIB.  QNIB is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright Christian Kniep, 2012

"""
This library interacts with a networkx graph.
The interaction between the postgres-DB and
the networkx-graph will be the focus.
"""

import sys
import pickle
from optparse import OptionParser
sys.path.append("~/Documents/QNIB/serverfiles/usr/local/lib/PyGreSQL")
sys.path.append('/Users/kniepbert/QNIB/serverfiles/usr/local/lib/')
sys.path.append('/Users/kniepbert/Documents/QNIB/serverfiles/usr/local/lib/')
import dbCon
import networkx as nx


class Parameter(object):
    """ parameter object to control script """
    def __init__(self):
        # Parameterhandling
        usage_str = "qnib2networkx [options]"
        self.parser = OptionParser(usage=usage_str)
        self.default()
        self.extra()
        self.debug = 0
        self.logfile = ""
        (self.options, args) = self.parser.parse_args()

        # copy over all class.attributes
        self.__dict__ = self.options.__dict__
        self.args = args

    def default(self):
        """ Default-Options """
        self.parser.add_option("-d", action="count", dest="debug",
            help="increases debug [default:None, -d:1, -ddd: 3]")
        self.parser.add_option("--logfile", dest="logfile",
            default="/tmp/qnib2networkx.log", action="store",
            help="qnib2networkx logfile (default: %default)")
        self.parser.add_option("-p", dest="pickle",
            default=False, action="store_true",
            help="if set the MultiGraph will be pickled")
        self.parser.add_option("--pfile", dest="picklefile",
            default="/tmp/qnib2networkx.p", action="store",
            help="file to pickle (default: %default)")

    def extra(self):
        """ optional options """
        pass

    def check(self):
        """ checking plausiblity """
        pass


class NXobj(object):
    """ parent of all nx_elements """
    def __init__(self, name, guid):
        self.guid = guid
        self.name = name

    def __eq__(self, other):
        """ if the guids match they eq """
        return self.guid == other.guid


class NXnode(NXobj):
    """ node object to handle graph element """
    def func(self):
        """ we'll see """
        pass


class NXedge(object):
    """ edge element """
    def __init__(self, src, dst):
        """ Initialize with NXnode objects """
        self.src = src
        self.dst = dst


class NXport(object):
    """ port element """
    def __init__(self, lid, p_int):
        pass


class QnibNetworkx(object):
    """ object to create and alter graph """
    def __init__(self):
        """ initialise object with clean graph """
        self.graph = nx.MultiGraph()

    def add_node(self, node):
        """ Add node with sys and node guid """
        self.graph.add_node(node.guid)

    def is_in(self, node):
        """ check whether the given node is in the graph or not"""
        return node.guid in self.graph

    def add_edge(self, src, edge, dst):
        """ connects src, dst with attributes """
        self.graph.add_edge(src.guid, dst.guid,
                            s_lid=edge.s_lid,
                            d_lid=edge.d_lid,
                            s_p_int=edge.s_p_int,
                            d_p_int=edge.d_p_int)


def split_link(acc):
    """ Spliting link informations """
    if acc['s_s_name']:
        name = acc['s_s_name']
        guid = acc['s_s_guid']
    else:
        name = acc['s_n_name']
        guid = acc['s_n_guid']
    src = NXnode(name, guid)
    if acc['d_s_name']:
        name = acc['d_s_name']
        guid = acc['d_s_guid']
    else:
        name = acc['d_n_name']
        guid = acc['d_n_guid']
    dst = NXnode(name, guid)

    edge = {}
    dst = {}
    src['n_id'] = acc['s_n_id']
    src['n_name'] = acc['s_n_name']
    src['n_state_id'] = acc['s_n_state_id']
    src['nt_name'] = acc['s_nt_name']
    src['s_name'] = acc['s_s_name'] 
    src['c_name'] = acc['s_c_name']
    src['s_id'] = acc['s_s_id']
    src['c_id'] = acc['s_c_id']
    src['guid'] = acc['s_s_guid']
    edge['s_lid'] = acc['s_p_lid']
    edge['s_p_id'] = acc['s_p_id']
    edge['s_p_int'] = acc['s_p_int']
    edge['d_p_lid'] = acc['d_p_lid']
    edge['d_p_id'] = acc['d_p_id']
    edge['d_p_int'] = acc['d_p_int']
    dst['n_id'] = acc['s_n_id']
    dst['n_name'] = acc['s_n_name']
    dst['n_state_id'] = acc['d_n_state_id']
    dst['nt_name'] = acc['d_nt_name']
    dst['s_name'] = acc['d_s_name']
    dst['c_name'] = acc['d_c_name']
    dst['s_id'] = acc['d_s_id']
    dst['c_id'] = acc['d_c_id']
    dst['guid'] = acc['d_s_guid']
    return (src, edge, dst)


def main():
    """ get all links and creates graph """
    opt = Parameter()
    dbcon = dbCon.dbCon(opt)
    q_net = QnibNetworkx()

    links = dbcon.getLinkList()
    while True:
        if len(links) == 0:
            break
        link = links.pop()
        (src, edge, dst) = split_link(link)
        
        if not q_net.is_in(src):
            q_net.add_node(src)
        if not q_net.is_in(dst):
            q_net.add_node(dst)
        q_net.add_edge(src, edge, dst)
        print edge

        continue

if __name__ == '__main__':
    main()