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
        self.pickle = False
        self.picklefile = ""
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
            default="/tmp/qnib2networkx", action="store",
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

    def get_type(self):
        """ returns type of obj """
        if type(self) == type(NXhost("", "")):
            return "node"
        elif type(self) == type(NXswitch("", "")):
            return "switch"

    def is_switch(self):
        """ Default the object ain't a switch """
        return False


class NXhost(NXobj):
    """ object to handle ib-hosts within the graph"""
    def func(self):
        """ wait for functionality """
        pass


class NXswitch(NXobj):
    """ object to handle ib-switches within the graph"""
    def func(self):
        """ wait for functionality """
        pass

    def is_switch(self):
        """ A switch is a switch """
        return True


class NXchassis(NXobj):
    """ object to handle ib-switches within the graph"""
    def func(self):
        """ wait for functionality """
        pass

    def is_switch(self):
        """ A chassis is also a switch """
        return True


class NXedge(object):
    """ edge element """
    def __init__(self, s_lid, s_pint, d_lid, d_pint):
        """ Initialize with NXnode objects """
        self.s_lid = s_lid
        self.s_pint = s_pint
        self.d_lid = d_lid
        self.d_pint = d_pint

    def func(self):
        """ wait for functionality """
        pass


class QnibNetworkx(object):
    """ object to create and alter graph """
    def __init__(self):
        """ initialise object with clean graph """
        self.m_graph = nx.MultiGraph()
        self.sw_graph = nx.MultiGraph()

    def edges(self):
        """ returns all edges """
        return self.m_graph.edges()

    def add_node(self, node):
        """ Add node with sys and node guid """
        if node.get_type() == "switch":
            self.sw_graph.add_node(node.name)
            self.sw_graph.node[node.name]['guid'] = node.guid
        self.m_graph.add_node(node.name)
        self.m_graph.node[node.name]['guid'] = node.guid

    def is_in(self, node):
        """ check whether the given node is in the graph or not"""
        return node.guid in self.m_graph

    def add_edge(self, src, edge, dst):
        """ connects src, dst with attributes """
        self.m_graph.add_edge(src.name, dst.name,
                            s_lid=edge.s_lid,
                            d_lid=edge.d_lid,
                            s_p_int=edge.s_pint,
                            d_p_int=edge.d_pint)
        if src.is_switch() and dst.is_switch():
            self.sw_graph.add_edge(src.name, dst.name,
                            s_lid=edge.s_lid,
                            d_lid=edge.d_lid,
                            s_p_int=edge.s_pint,
                            d_p_int=edge.d_pint)

    def pickle_mgraph(self, pfile):
        """ Dump multigraph with pickle """
        filed = open(pfile + ".mg", "wb")
        pickle.dump(self.m_graph, filed)
        filed.close()

    def pickle_swgraph(self, pfile):
        """ Dump switch graph with pickle """
        filed = open(pfile + ".sw", "wb")
        pickle.dump(self.sw_graph, filed)
        filed.close()

    def __str__(self):
        """ print formated network """
        res = "s"
        # ss
        return res


def split_link(acc):
    """ Spliting link informations """
    # If its an chassis we create a chassis node
    if acc['s_c_name'] != 'empty':
        name = acc['s_c_name']
        guid = acc['s_c_name']
    elif acc['s_s_name']:
        name = acc['s_s_name']
        guid = acc['s_s_guid']
    else:
        name = acc['s_n_name']
        guid = acc['s_n_guid']
    if acc['s_nt_name'] == "switch":
        src = NXswitch(name, guid)
    elif acc['s_nt_name'] == "host":
        src = NXhost(name, guid)
    else:
        raise IOError("node type !(host|switch|chassis)")
    if acc['d_c_name'] != 'empty':
        name = acc['d_c_name']
        guid = acc['d_c_name']
    elif acc['d_s_name']:
        name = acc['d_s_name']
        guid = acc['d_s_guid']
    else:
        name = acc['d_n_name']
        guid = acc['d_n_guid']
    if acc['d_nt_name'] == "switch":
        dst = NXswitch(name, guid)
    elif acc['d_nt_name'] == "host":
        dst = NXhost(name, guid)
    else:
        raise IOError("node type !(host|switch|chassis)")

    s_lid = acc['s_p_lid']
    s_pint = acc['s_p_int']
    d_lid = acc['d_p_lid']
    d_pint = acc['d_p_int']
    edge = NXedge(s_lid, s_pint, d_lid, d_pint)
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
    if opt.pickle:
        q_net.pickle_mgraph(opt.picklefile)
        q_net.pickle_swgraph(opt.picklefile)

if __name__ == '__main__':
    main()
