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
    def __init__(self, guid, name=None):
        self.guid = guid
        self.name = name
        self.nodeguid = None
        self.nodename = None
        self.chassisguid = None
        self.chassisname = None
        self.switchname = None
        self.asic_count = 0
        self.typ = None
        self.is_switch = False
        self.is_host = False
        self.is_chassis = False

    def __eq__(self, other):
        """ if the guids match they eq """
        return self.guid == other.guid

    def get_typ(self):
        """ return type """
        return self.typ


class NXsystem(NXobj):
    """ object to handle ib-systems within the graph"""
    def __init__(self, guid):
        NXobj.__init__(self, guid)
        self.typ = "system"
        self.cnt_ports = 1
        self.lid = 0

    def update_chassis(self, chassisname):
        """ Update chassis attributes """
        self.chassisname = chassisname

    def update_switch(self, swports, nguid, nname, lid):
        """ if systems turns out to be a switch, it is updated """
        self.is_switch = True
        if self.name == None:
            self.name = nname
        self.cnt_ports = swports
        self.nodeguid = nguid
        self.nodename = nname
        self.lid = lid

    def update_host(self, nguid, nname):
        """ if systems turns out to be a host, it is updated """
        self.is_host = True
        self.nodeguid = nguid
        self.nodename = nname

    def create_switch(self):
        """ If turns out to be a switch(node) create a node and return """
        switch = NXswitch(self.nodeguid, self.nodename, \
                          self.cnt_ports, self.lid)
        return switch

    def create_node(self):
        """ Returns a node to add to the ib_graph """
        node = NXnode(self.nodeguid, self.nodename)
        if self.is_chassis:
            node.set_switch(self.chassisname)
        elif self.is_switch:
            node.set_switch(self.nodename)
        elif self.is_host:
            node.set_host(self.nodename)
        return node


class NXhost(NXobj):
    """ object to handle ib-hosts within the graph"""
    def __init__(self, guid, name):
        NXobj.__init__(self, guid, name)
        self.typ = "host"


class NXnode(NXobj):
    """ object to be a node (host/switch) within the ib graph """
    def __init__(self, guid, name):
        """ create a nodeinstance with enherited vals from switchsystem """
        NXobj.__init__(self, guid, name)
        self.typ = "node"

    def set_switch(self, switchname):
        """ if node is a switch we should know to handle edges """
        self.switchname = switchname
        self.is_switch = True

    def set_host(self, nodename):
        """ what shall we do if node is a host """
        self.is_host = True


class NXswitch(NXobj):
    """ object to handle ib-switches within the graph"""
    def __init__(self, guid, name, cnt_ports=0, lid=0):
        """ create an switchinstance with enherited vals from switchsystem """
        NXobj.__init__(self, guid, name)
        self.typ = "switch"
        self.cnt_ports = cnt_ports
        self.lid = lid
        self.is_switch = True
        self.is_singular = False

    def set_singluar(self):
        """ if its one ASIC asigned to a switch we set it"""
        self.is_singular = True


class NXchassis(NXobj):
    """ object to handle ib-switches within the graph"""
    def func(self):
        """ wait for functionality """
        pass


class NXedge(object):
    """ edge element """
    def __init__(self, src, s_pint, s_pext,
                 dst, d_pint, d_pext, width, speed):
        """ Initialize with NXnode objects """
        self.src = src
        self.dst = dst
        self.s_pint = s_pint
        self.s_pext = s_pext
        self.d_pint = d_pint
        self.d_pext = d_pext
        self.width = width
        self.speed = speed
        self.is_interswitch = self.src.is_switch and self.dst.is_switch

    def __str__(self):
        """ printing edge in human readable way """
        res = "%s(%s)<>(%s)%s" % (self.src.name, type(self.src),
                                  type(self.dst), self.dst.name)
        res += " %sx%s" % (self.width, self.speed)
        return res


class QnibNetworkx(object):
    """ object to create and alter graph """
    def __init__(self, opt):
        """ initialise object with clean graph """
        self.opt = opt
        # ib-graph with all real objects
        self.ib_graph = nx.MultiGraph()
        # logical view with human readable switches
        self.sw_graph = nx.MultiGraph()
        # list of systems
        self.systems = {}

    def deb(self, msg, level=1):
        """ print debug information """
        if level <= self.opt.debug:
            print msg

    def edges(self):
        """ returns all edges """
        return self.ib_graph.edges()

    def add_switch(self, switch):
        """ Add switch to switchgraph """
        # check if its a switch
        if not switch.is_switch:
            raise IOError("%s ain't a switch %s (is_switch:%s" % \
                          (switch.name, type(switch),switch.is_switch))
        # If we are a chassis or an independent switch,
        # we are added to the switch graph
        if switch.name not in self.sw_graph.nodes():
            self.deb("Adding %s: %s" % (switch.get_typ(), switch.name))
            self.sw_graph.add_node(switch.name)
            self.sw_graph.node[switch.name]['node'] = switch

    def add_node(self, node):
        """ Add ib node to the node graph """ 
        # if the node is a real IB-entity, we are added to the ib-graph
        self.ib_graph.add_node(node.guid)
        self.ib_graph.node[node.guid]['node'] = node

    def get_node(self, nguid):
        """ returns the NXnode object with given nguid"""
        try:
            return self.ib_graph.node[nguid]['node']
        except KeyError, e:
            self.pickle_ibgraph
            self.pickle_swgraph
            print nguid
            raise KeyError(e)

    def get_switch(self, sw_name):
        """ returns the NXnode object with given nguid"""
        try:
            return self.sw_graph.node[sw_name]['node']
        except KeyError, e:
            self.pickle_ibgraph
            self.pickle_swgraph
            print sw_name
            raise KeyError(e)

    def add_sys(self, system):
        """ add a system to the list """
        if system.guid not in self.systems.keys():
            self.systems[system.guid] = system

    def get_sys(self, sysimgguid):
        """ get a system out of the system-dict (should be a graph?)"""
        return self.systems[sysimgguid]

    def update_sys_switch(self, sysimgguid, switchguid, switchname):
        """ update the switchguid/-name of system identified with systemguid """
        self.systems[sysimgguid].update_switchguid(switchguid)
        self.systems[sysimgguid].update_switchname(switchname)

    def dst_not_in(self, nguid):
        """ determin whether a nodeguid of a switchport destination is in """
        check = not nguid in self.ib_graph
        if not check:
            self.deb("Destination '%s' in the graph: \n %s" % \
                     (nguid, ",".join(self.ib_graph.nodes())), 2)
        return check

    def is_in(self, node):
        """ check whether the given node is in the graph or not"""
        return node.guid in self.ib_graph

    def add_edge(self, src, edge, dst):
        """ connects src, dst with attributes """
        self.ib_graph.add_edge(src.name, dst.name,
                            s_p_int=edge.s_pint,
                            d_p_int=edge.d_pint)
        if edge.is_interswitch:
            self.deb("Adding interswitch edges: %s" % edge)
            self.sw_graph.add_edge(src.name, dst.name,
                            s_p_int=edge.s_pint,
                            d_p_int=edge.d_pint)
        else:
            self.deb("Edge ain't interswitch edges: %s" % (edge))

    def pickle_ibgraph(self, pfile):
        """ Dump IB-multigraph with pickle """
        filed = open(pfile + ".ibg", "wb")
        pickle.dump(self.ib_graph, filed)
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
        src = NXswitch(guid, name)
    elif acc['s_nt_name'] == "host":
        src = NXhost(guid, name)
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
        dst = NXswitch(guid, name)
    elif acc['d_nt_name'] == "host":
        dst = NXhost(guid, name)
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
        q_net.pickle_ibgraph(opt.picklefile)
        q_net.pickle_swgraph(opt.picklefile)

if __name__ == '__main__':
    main()
