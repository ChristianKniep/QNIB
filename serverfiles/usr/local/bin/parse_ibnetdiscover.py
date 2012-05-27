#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
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

import re
import os
import sys
import commands
from optparse import OptionParser
import datetime


sys.path.append('/Users/kniepbert/QNIB/serverfiles/usr/local/lib/')
sys.path.append('/Users/kniepbert/Documents/QNIB/serverfiles/usr/local/lib/')
import lib_topology
import qnib2networkx as qnx


class Parameter(object):
    """ Object to hold and eval arguments """
    def __init__(self):
        # Parameterhandling
        usage_str = "parse_ibnetdiscover [options]"
        self.parser = OptionParser(usage=usage_str)
        self.default()
        self.extra()
        self.loop = ""
        self.debug = 0
        self.lids = ""
        self.file = ""
        self.cfgfile = ""
        self.logfile = ""
        (self.options, args) = self.parser.parse_args()

        # copy over all class.attributes
        self.__dict__ = self.options.__dict__
        self.args = args

    def default(self):
        """ Default-Options """
        self.parser.add_option("-d", action="count", dest="debug",
            help="increases debug [default:None, -d:1, -ddd: 3]")
        self.parser.add_option("-f", dest="file", default="", action="store",
            help="file which contains the ibnetdiscover-output")
        self.parser.add_option("--logfile", dest="logfile",
                default="/var/log/parse_ibnetdiscover.log", action="store",
                help="file which contains the ibnetdiscover-output")
        self.parser.add_option("-L", dest="lids", default=False, action="store",
            help="lid to debug (all other debug information will be supressed)")
        self.parser.add_option("--check-traps", dest="check_traps",
            default=False, action="store_true",
            help="check for traps stored in the DB inserted from opensm")
        self.parser.add_option("-c", dest="cfgfile",
            default="/root/QNIB/serverfiles/usr/local/etc/default.cfg",
            action="store", help="Configfile (default: %default)")
        self.parser.add_option("-g", dest="graph", default=None,
            action="store", help="Graph to create (default: %default)")
        self.parser.add_option("--graphviz-cmd", dest="graphviz_cmd",
            default="twopi", action="store",
            help="Graphviz cmd to layout graph (default: %default)")
        self.parser.add_option("--pfile", dest="picklefile",
            default="/tmp/pickle", action="store",
            help=" (default: %default)")
        self.parser.add_option("--ibsim", dest="ibsim",
            default=False, action="store_true",
            help="if we are running with ibsim, we have to PRELOAD libumad.so")
        self.parser.add_option("--loop", dest="loop", default=False,
            action="store_true", help="Loop the script")
        self.parser.add_option("--delay", dest="loop_delay",
            default=10, action="store",
            help="Delay in seconds if loop is set (default: %default)")
        self.parser.add_option("--parse", dest="parse",
            default=False, action="store_true",
            help="Show parsing debug information")
        self.parser.add_option("--circle", dest="circle", default=False,
            action="store_true", help="Show circle debug information")
        self.parser.add_option("--links", dest="links", default=False,
            action="store_true", help="Show link analysis debug information")
        self.parser.add_option("--force-uptopo", dest="force_uptopo",
            default=False, action="store_true",
            help="Force update of topology")

    def extra(self):
        """ optional options """
        pass

    def check(self):
        """ checking plausiblity """
        if self.debug == None:
            self.debug = 0
        if self.lids:
            lids = self.lids.split(",")
            self.lids = set(lids)
        self.node_guids = {}


def has_items(l_1, l_2):
    """ checks whether l_1 has at least one item in l_2 """
    for item in l_1:
        check = item in l_2
        if check:
            return True
    return False


class SWport(object):
    """ Parent object of switchport handling..."""
    def __init__(self, opt, switch, line, match):
        self.line = line
        self.opt = opt
        self.switch = switch
        self.match = match
        self.dportguid = 'new'
        self.ext_port = False
        self.dext_port = False
        self.port = None
        self.type = None
        self.dguid = None
        self.dport = None
        self.dname = None
        self.dlid = None
        self.width = None
        self.speed = None

    def __str__(self):
        """ print object informations """
        res = ""
        res += self.line
        res += "match.groups():[%s]" % ", ".join(self.match.groups())
        res += "dportguid:%(dportguid)s" % self.__dict__
        return res

    def deb(self, lids, msg, deb=0):
        """ prints debug message """
        if self.opt.lids and has_items(lids, self.opt.lids):
            print msg
        elif self.opt.parse and self.opt.debug >= deb:
            print msg

    def matching(self):
        """ extract matching groups """
        (self.port, self.type, self.dguid, self.dport, self.dportguid,
         self.dname, self.dlid, self.width, self.speed) = self.match.groups()
        print self.dportguid

    def eval(self, cfg):
        """ evaluates input """
        self.matching()
        # Meine Switchports zuerst
        switch = self.switch
        src = switch.createPort(self.port, '', switch.lid)

        try:
            mat = re.search("([a-z0-9]+)", self.dportguid, re.I)
        except TypeError, err:
            print self
            raise TypeError(err)
        # TODO: Muss ich hier unterscheiden? Hoffe nicht.... :)
        if mat:
            self.dportguid = mat.group(1)
        else:
            self.dportguid = ''
        s_lids = switch.getLids()
        s_lids.add(self.dlid)
        msg = "Matche Switch-Port: p:%s dguid:%s" % (self.port, self.dguid)
        msg += "dp:%s dpguid:%s dn:%s dl:%s w:%s s:%s" % \
            (self.dport, self.dportguid, self.dname,
             self.dlid, self.width, self.speed)


class SwPortExt(SWport):
    def matching(self):
        (self.port, self.ext_port, self.type, self.dguid, self.dport,
         self.dportguid, self.dname, self.dlid, self.width,
         self.speed) = self.match.groups()


class SwPortDExt(SWport):
    """ SourcePort is not modular - DstPort is """
    def matching(self):
        (self.port, self.type, self.dguid, self.dport, self.dext_port,
         self.dname, self.dlid, self.width, self.speed) = self.match.groups()


class SwPortExtExt(SWport):
    def matching(self):
        (self.port, self.ext_port, self.type, self.dguid, self.dport,
         self.dext_port, self.dname, self.dlid, self.width,
         self.speed) = self.match.groups()


class Parsing(object):
    """ parsing object which holds the functionality """
    def __init__(self, options, cfg, log):
        self.q_net = qnx.QnibNetworkx()
        self.cfg = cfg
        self.opt = options
        self.log = log
        self.log.start("create")
        self.log_file = self.opt.logfile
        self.ret_ec = 0
        self.start = int(datetime.datetime.now().strftime("%s"))
        self.status_list = []
        self.chassis = {}
        self.perf_list = []
        self.host_pat = cfg.get('hostpat')
        self.chassis_names = cfg.get('chassis')
        self.sys_guids = {}
        self.sw_ports = []
        self.sysimgguid = None
        self.wall = 0
        self.chip = None
        self.nodeguid = None
        self.l_board = None
        self.f_board = None
        self.chassis_guid = None
        self.chassis_name = None

    def dump_graphs(self):
        """ pickle the graphs """
        self.q_net.pickle_ibgraph(self.opt.picklefile)
        self.q_net.pickle_swgraph(self.opt.picklefile)

    def eval_swports(self, cfg):
        """ evaluates all found switchports """
        for swp in self.sw_ports:
            swp.eval(cfg)

    def get_ibnetdiscover(self):
        """ gets the lines of ibnetdiscover / given file """
        if self.opt.file == "":
            cmd = "sudo  "
            if self.opt.ibsim:
                cmd += "LD_PRELOAD=/usr/local/lib/umad2sim/libumad2sim.so"
                cmd += ":/usr/lib64/umad2sim/libumad2sim.so "
            cmd += "/usr/local/sbin/ibnetdiscover -g"
            (errc, out) = commands.getstatusoutput(cmd)
            if errc != 0:
                self.status_list = [out + "ibnetdiscover failed"]
                self.ret_ec = 2
            lines = out.split("\n")
        else:
            fdesc = open(self.opt.file, "r")
            lines = fdesc.readlines()
            fdesc.close()
        return lines

    def reset_board(self):
        """ FWIW initialize all board stuff """
        self.print_board()
        self.chassis_guid = None
        self.chassis_name = None
        return all(map(lambda x: x == None, \
                (self.chassis_guid, self.chassis_name)))

    def set_chassis(self, chassis_guid, chassis_name):
        """ set chassisvars to use them in systems/nodes to come """
        self.chassis_guid = chassis_guid
        self.chassis_name = chassis_name

    def get_chassis(self):
        """ get stored chassis information """
        return (self.chassis_guid, self.chassis_name)

    def print_board(self):
        """ print chassis informations """
        if not all(map(lambda x: x == None, \
                (self.chassis_guid, self.chassis_name))):
            print "chassisGuid:%s chassisName:%s" % \
                (self.chassis_guid, self.chassis_name)
        #else:
        if False:
            print "nothing to reset"

    def ibnetdiscover(self):
        """ eval ibnetdiscover and creates networkx.MultiGraph """

        lines = self.get_ibnetdiscover()
        self.reset_board()

        # Identifing switches nodeguid, chassisguid and nameregex
        for line in lines:
            if self.match_continue(line):
                continue

            # Reset von allen Board-Spezifika
            reg = "^vendid.*"
            mat = re.match(reg, line)
            if mat:
                continue

            if self.match_chassis(line):
                continue
            if self.match_system(line):
                continue
            # Modulare Switches
            if self.match_switch(line):
                continue
            # CA
            if self.match_ca(line):
                continue
            # Edges
            if self.match_switchport_gen(line):
                continue

        end = int(datetime.datetime.now().strftime("%s"))
        self.wall = end - self.start

    def match_chassis(self, line):
        """ matches chassis lines """
        ## Chassis 1 (guid 0x8f104004050c6)
        reg = "Chassis (\d+) \(guid 0x([0-9a-f]+)\)"
        mat = re.match(reg, line)
        if mat:
            (c_nr, c_guid) = mat.groups()
            name = self.chassis_names[c_guid]['name']
            cname = self.eval_name(name)[0]
            self.set_chassis(c_guid, cname)
            chassis = qnx.NXchassis(c_guid, cname)
            self.q_net.add_node(chassis)
        return mat

    def match_continue(self, line):
        """ All regardless lines are matched """
        # HCA-Zeilen
        # [1](guid)
        reg = '^\[1\]\(.*'
        #if re.match(r,line): continue

        # Leerzeilen
        reg = '^[ \t]+$'
        if re.match(reg, line):
            return True
        # vendid/devid/caguid
        reg = '^(vend|dev|cagu)id.*'
        if re.match(reg, line):
            return True
        # Auskommentiertes
        reg = '^#.*'
        if re.match(reg, line):
            return True
        return False

    def match_switchport_gen(self, line):
        """ generic switchportmatching """
        # while riding the train it seems clever to skip links where
        # the destination is not in the graph yet
        # if not in, it will be matched when it is time
        # to be specific: when the destination is the source
        if self.match_switchport_extext(line):
            return True
        if self.match_switchport_ext(line):
            return True
        if self.match_switchport_dext(line):
            return True
        if self.match_switchport(line):
            return True
        return False

    def match_switchport_extext(self, line):
        """ Matching two external switchports """
        #[14][ext 2]	"S-0008f104003f5c40"[24][ext 15]
        # "ISR9288/ISR9096 Voltaire sLB-24" lid 208 4xSDR
        #[15][ext 15]    "S-0008f104003f5c43"[22][ext 19]
        # "ISR9288/ISR9096 Voltaire sLB-24" lid 211 4xSDR
        reg = "^\[(\d+)\]\[ext (\d+)\][ \t]+\"[SH]-[0]*([a-z0-9]+)\""
        reg += "\[(\d+)\]\[ext (\d+)\].*#[ \t]+\".*\""
        reg += "[ \t]+lid[ \t]\d+ (\d+)x([A-Z]DR)"
        mat = re.match(reg, line)
        if mat:
            # if dst not yet in the graph, skip it
            (s_pint, s_pext, d_nguid, d_pint, d_pext,
             width, speed) = mat.groups()
            if self.q_net.dst_not_in(d_nguid):
                return True
            else:
                # while we all meet within the graph lets insert the link
                src = self.q_net.get_node(self.nodeguid)
                dst = self.q_net.get_node(d_nguid)
                edge = qnx.NXedge(src, s_pint, s_pext,
                                  dst, d_pint, d_pext,
                                  width, speed)
                self.q_net.add_edge(src, edge, dst)
                return True
        return False

    def match_switchport_ext(self, line):
        """ Matching switchport with external port to normal port """
        reg = "^\[(\d+)\]\[ext (\d+)\][ \t]+\"[SH]-[0]*([a-z0-9]+)\""
        reg += "\[(\d+)\].*#[ \t]+\".*\"[ \t]+lid[ \t]\d+ (\d+)x([A-Z]DR)"
        mat = re.match(reg, line)
        if mat:
            (s_pint, s_pext, d_nguid, d_pint,
             width, speed) = mat.groups()
            if self.q_net.dst_not_in(d_nguid):
                return True
            else:
                # while we all meet within the graph lets insert the link
                src = self.q_net.get_node(self.nodeguid)
                dst = self.q_net.get_node(d_nguid)
                edge = qnx.NXedge(src, s_pint, s_pext,
                                  dst, d_pint, None,
                                  width, speed)
                self.q_net.add_edge(src, edge, dst)
                return True
        return False

    def match_switchport_dext(self, line):
        """ Matching (nonexternal) switchport with external port """
        #Sw [1]  "S-0008f104003f63de"[14][ext 14]
        reg = "^\[(\d+)\][ \t]+\"[SH]-[0]*([a-z0-9]+)\"\[(\d+)\]\[ext (\d+)\]"
        reg += ".*#[ \t]+\".*\"[ \t]+lid[ \t]\d+ (\d+)x([A-Z]DR)"
        mat = re.match(reg, line)
        if mat:
            (s_pint, d_nguid, d_pint, d_pext, width, speed) = mat.groups()
            if self.q_net.dst_not_in(d_nguid):
                return True
            else:
                # while we all meet within the graph lets insert the link
                src = self.q_net.get_node(self.nodeguid)
                dst = self.q_net.get_node(d_nguid)
                edge = qnx.NXedge(src, s_pint, None,
                                  dst, d_pint, d_pext,
                                  width, speed)
                self.q_net.add_edge(src, edge, dst)
                return True
        return False

    def match_switchport(self, line):
        """ Matching simplest switchport (no external ports) """
        reg = "^\[(\d+)\][ \t]+\"[SH]-[0]*([a-z0-9]+)\""
        reg += "\[(\d+)\].*#[ \t]+\".*\"[ \t]+lid[ \t]\d+ (\d+)x([A-Z]DR)"
        mat = re.match(reg, line)
        if mat:
            (s_pint, d_nguid, d_pint,
             width, speed) = mat.groups()
            if self.q_net.dst_not_in(d_nguid):
                return True
            else:
                # while we all meet within the graph lets insert the link
                src = self.q_net.get_node(self.nodeguid)
                dst = self.q_net.get_node(d_nguid)
                edge = qnx.NXedge(src, s_pint, None,
                                  dst, d_pint, None,
                                  width, speed)
                self.q_net.add_edge(src, edge, dst)
                return True
        return False

    def match_ca(self, line):
        """ matching channeladapter (network card) """
        reg = '.*H-[0]*([a-z0-9]+).*# "(.*)".*'
        mat = re.match(reg, line)
        if mat:
            (guid, name) = mat.groups()
            nname = self.eval_name(name)[0]
            self.nodeguid = guid
            host = qnx.NXhost(guid, nname)
            self.q_net.add_node(host)
            return True
        return False

    def match_system(self, line):
        """ systemguid eines Chassis """
        # Board of a modular switch
        reg = "sysimgguid=0x([0-9a-f]+)[ \t]+# Chassis (\d+)"
        mat = re.match(reg, line)
        if mat:
            self.sysimgguid = mat.group(1)
            system = qnx.NXsystem(self.sysimgguid, None)
            self.q_net.add_sys(system)
            return True
        # systemguid
        reg = "sysimgguid=0x([0-9a-f]+)"
        mat = re.match(reg, line)
        if mat:
            self.reset_board()
            self.sysimgguid = mat.group(1)
            system = qnx.NXsystem(self.sysimgguid, None)
            self.q_net.add_sys(system)
            return True
        return False

    def match_switchguid(self, line):
        """ extract the switchguid out of ibnetdiscover """
        ## in newer switches the systemguid==switchguid
        # switchguid=0x8f105002011c8(8f105002011c8)	#
        reg_wo_name = "switchguid=0x([0-9a-f]+).*"
        mat_wo_name = re.match(reg_wo_name, line)
        if  mat_wo_name:
            guid = mat_wo_name.groups(1)
            name = None
        ## but older switches refer to there switchguid(!=systemguid) when
        ## addressing the switchports, so we better be
        ## sure to have the big picture
        # switchguid=0x8f104004050c7(8f104004050c7)	# ISR2004 Spine 1 Chip 1
        reg = "switchguid=0x([0-9a-f]+)\((?:[0-9a-f]+)\) # (.*)"
        mat = re.match(reg, line)
        if  mat:
            (guid, name) = mat.groups()
        if mat or mat_wo_name:
            self.q_net.update_sys_switch(self.sysimgguid, guid, name)
            return True
        else:
            return False

    def match_switch(self, line):
        """ switches are matched here """
        # if a chassis is given it will be handeled
        #Switch	24 "S-0008f104003f58ef"	# "name" base port 0 lid 203 lmc 0
        reg = 'Switch[ \t]+([0-9]+)[ \t]+"S-[0]*([a-z0-9]+).*#'
        reg += '[ \t]+"(.*)".*lid[ \t]+(\d+)[ \t]+lmc'
        mat = re.match(reg, line)
        if  mat:
            # the evaluated name will be the nodename
            # -> seems to describe the moduletype in older modulare switches
            # -> modern mod. switches describes the hostname (so human readable)
            # previously we extracted
            #  * chassisname (given chassisid should be maped within the cfg)
            #   -> the for sure human readable one [sig!]
            #  * switchname  (appended to the switchguid like Lineboard9 Chip1)
            #   -> importent to know which module of the switch is handled
            (swports, nguid, name, lid) = mat.groups()

            # if we are in a chassis we should have informations stored
            (c_guid, c_name) = self.get_chassis()
            if c_guid != None:
                # if so, we name the node with the chassis-name
                switch = self.q_net.get_switch(c_name)
            else:
                self.nodeguid = nguid
                nname = self.eval_name(name)[0]
                # if we match here, switch-/sysimgguid _has_ to be given
                # therefore we can adress the system
                system = self.q_net.get_sys(self.sysimgguid)
                if type(system) == type(None):
                    # We got a singular switch, so we create a chassis ans system
                    # for the switchgraph
                    chassis = qnx.NXchassis(nguid, nname)
                    system = qnx.NXsystem(nguid, nname)
                system.update_switch(swports, nguid, nname, lid)
                switch = system.create_node()
            self.q_net.add_node(switch)
        return mat

    def eval_name(self, name):
        """ eval the hostname to craft out human readable ones """
        new_type = None
        new_name = name
        reg = "(%s)" % "|".join(self.host_pat.keys())
        mat = re.match(reg, name, re.I)
        if mat:
            for reg in self.host_pat.keys():
                mat = re.match("^%s$" % reg, name, re.I)
                if mat:
                    if 'regname' in self.host_pat[reg].keys():
                        # Regname formatiert die groups des regex neu
                        # X,Y sind platzhalter fuer die jeweiligen Matches
                        # Bei X wird die aktuelle Gruppe eingetragen
                        # Y wird ausgelassen,
                        #   z.B. wenn man oder matched '(spine|line)' 
                        regname = self.host_pat[reg]['regname']
                        res = ""
                        cnt = 1
                        for letter in regname:
                            if letter == "X":
                                res += mat.group(cnt)
                                cnt += 1
                            elif letter == "Y":
                                cnt += 1
                            else:
                                res += letter
                        new_name = res
                    if 'type' in self.host_pat[reg].keys():
                        # hmm... what about the type
                        new_type = self.host_pat[reg]['type']
                    if 'name' in self.host_pat[reg].keys():
                        new_name = self.host_pat[reg]['name']
                    if 'short' in self.host_pat[reg].keys():
                        new_name = "%s%s" % \
                                   (self.host_pat[reg]['short'], mat.group(2))
        return new_name, new_type

    def __str__(self):
        if   self.ret_ec == 0:
            ret_txt = "OK"
        elif self.ret_ec == 1:
            ret_txt = "WARN"
        elif self.ret_ec == 2:
            ret_txt = "CRIT"
        ret_txt += " - %s | %s" % (", ".join(self.status_list),
                                  ", ".join(self.perf_list))

        # perfdata
        return ret_txt

    def add_perf(self, key, val):
        """ Add performance val/key to nagios-string """
        if val != '0':
            self.status_list.append(" %s %s" % (val, key))
        self.perf_list.append("%s=%s" % (key, val))

    def get_ec(self):
        """ returns the current ec """
        return self.ret_ec

    def deb(self, lids, msg, typ, deb):
        """ prints information of given kind (if set in options) """
        if self.opt.lids:
            if has_items(lids, self.opt.lids):
                print msg
        elif typ == 'p' and self.opt.parse and self.opt.debug >= deb:
            print msg
        elif typ == 'l' and self.opt.links and self.opt.debug >= deb:
            print msg

    def dump_log(self):
        """ writes nagiosmsg to file where it can be found """
        filed = open(self.log_file, "a")
        msg = "%s \n" % self.__str__()
        filed.write(msg)
        filed.close()

    def create_graphs(self):
        """ creates graph """
        pass


def main():
    """ Main function to rule the script """
    open('/tmp/parse_ibnetdiscover.lock', 'w').close()
    options = Parameter()
    options.check()
    cfg = lib_topology.config([options.cfgfile, ], options)
    cfg.eval()
    log = lib_topology.log_c(options, options.logfile)

    par = Parsing(options, cfg, log)
    log.debug("ibnetdiscover", 0)
    par.ibnetdiscover()
    log.debug("evalSwPorts", 0)
    #par.eval_swports(cfg)
    #if len(trap_dict) > 0 or options.force_uptopo:
        # Should we update the topology?
        # -> A new node appears
        # -> User removed a node for good
        #par.update_topo()
        #par.create_graphs()

    #else:
    #    log.debug("%s Traps detected..." % len(trap_dict), 1)

    # we sure should redraw the graph to visualize the traffic
    par.dump_log()
    os.remove('/tmp/parse_ibnetdiscover.lock')
    errc = par.get_ec()
    print par.dump_graphs()
    print par
    sys.exit(errc)


# ein Aufruf von main() ganz unten
if __name__ == "__main__":
    main()
