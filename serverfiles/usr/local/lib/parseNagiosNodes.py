#!/etc/venus/current/bin/python
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

import re,os,sys, time,commands
import optparse

class Parameter(object):
    def __init__(self,argv):
        # Parameterhandling
        usageStr = "parseNagiosNodes [options]"
        self.parser = optparse.OptionParser(usage=usageStr)
       
        self.parser.add_option("-d",
            action="count",
            dest="debug",
            help="increases debug [default:None, -d:1, -ddd: 3]")
       
        self.default()

        (self.options, args) = self.parser.parse_args()

        # copy over all class.attributes
        self.__dict__ = self.options.__dict__
        self.args = args
       
    def default(self):
        pass

    def check(self):
	pass

class parse(object):
    def __init__(self):
	pass
   
    def eval(self):
	self.res    = {}
	fd = open('/usr/local/nagios/etc/nagios.cfg')
	lines = fd.readlines()	
	r="^cfg_dir=([/a-z\.]+)"
	# Mapreduce um die cfg-Files zu finden :)
	cfgDirs = [re.match(r,x).group(1) for x in lines if re.match(r,x)]
	for dir in cfgDirs:
	    hostCfgs = os.listdir(dir)
	    for cfg in hostCfgs:
		path = "%s/%s" % (dir,cfg)
		fd = open(path)
		lines = fd.readlines()
		hBool = True
		gBool = True
		for line in lines:
		    if not hBool and not gBool: break
		    if hBool:
			r=".*host_name[ \t]+([a-zA-Z0-9\-]+).*"
			m = re.match(r,line)
			if m: 
			    host = m.group(1)
			    self.res[host] = {'cat':dir.split("/")[-1]}
			    hBool = False
		    if gBool:
			r=".*_GUID[ \t]+([0-9a-z]+).*"
			m = re.match(r,line)
			if m: 
			    self.res[host]['guid'] = m.group(1) 
			    gBool = False
	return self.res

def main(argv=None):
    # Parameter
    options = Parameter(argv)
    options.check()
    
    
# ein Aufruf von main() ganz unten
if __name__ == "__main__":
   main()
