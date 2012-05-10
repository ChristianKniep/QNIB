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
from optparse import OptionParser
sys.path.append("~/Documents/QNIB/serverfiles/usr/local/lib/PyGreSQL")
sys.path.append('/Users/kniepbert/QNIB/serverfiles/usr/local/lib/')
sys.path.append('/Users/kniepbert/Documents/QNIB/serverfiles/usr/local/lib/')
import dbCon


class Parameter(object):
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

    def extra(self):
        """ optional options """
        pass

    def check(self):
        """ checking plausiblity """
        pass

class qnibNetworkx(object):
    def __init__(self):
        pass


def main():
    opt = Parameter()
    dbcon = dbCon.dbCon(opt)
    q_net = qnibNetworkx()

    systems = dbcon.getSystems()
    changed_sids = []
    while True:
        if len(systems) == 0:
            break
        system = systems.pop()
        print system
        continue
        ## Wenn der Knoten ein Chassis-Knoten ist, dann...
        if system.isChassis():
            # gehen erstmal alle Lampen an, stimmt das ueberhaupt noch?
            raise IOError("sure thats working?")
            # Infos setzen, falls noch nicht getan
            back = self.cDB.getSystem(system.s_id)
            # Erstellen wir Stelv-Knoten
            chassis_sys = self.cDB.addChassis(system)
            # Loesche alle Knoten aus meiner Systems-Liste,
            # die dem Chassis angehoeren
            delSys = [x for x in systems]
            # Da system schon aus systems raus ist, behandeln wir
            # ihn separat... irgendwie schon schmerzhaft
            changedSids.extend(chassis_sys.drainSys(system))
            for delCandidate in delSys:
                if delCandidate.c_id==chassis_sys.c_id:
                    systems.remove(delCandidate)
                    changedSids.extend(chassis_sys.drainSys(delCandidate))

                else:
                    pass
            switches.append(chassis_sys)
        elif system.nt_name in ("root"):
            roots.append(system)
            self.deb("Appende Root: %s" % system,1)
        elif system.nt_name in ("switch"):
            switches.append(system)
            self.deb("Appende Switch: %s" % system,1)
        else:
            systemsNext.append(system)

if __name__ == '__main__':
    main()