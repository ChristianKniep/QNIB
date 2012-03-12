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
# -*- coding: utf-8 -*-

# Bibliotheken laden
import re, os, sys, commands,time
from optparse import OptionParser
import pg, pgdb, datetime

class debug(object):
    def __init__(self,opt,file):
        self.opt = opt
        self.dl  = opt.debug
        self.file = file
    def setHost(self,host):
        self.host = host
    def deb(self,msg,level=3):
        if level<=self.dl or (self.dl==None and level<=2):
            if self.host.startswith("8"):
                if self.host=="8f1040399094f": self.host = "kempes"
                elif self.host=="8f104039901d7": self.host = "maradonna"
                elif self.host=="8f10403990947": self.host = "platini"
                elif self.host=="8f10403990a7f": self.host = "ibeat1"
                elif self.host=="8f104004127bd": self.host = "voltaire1"
            dt = datetime.datetime.now()
            date = dt.strftime("%m-%d %H:%M:%S")
            m = "%s:%-10s %-6s %-15s >> %s\n" % (date,dt.microsecond,os.getpid(), self.host,msg)
            fd = open(self.file,"a")
            fd.write(m)
            fd.close()

def main(): pass
            
# ein Aufruf von main() ganz unten
if __name__ == "__main__":
    main()