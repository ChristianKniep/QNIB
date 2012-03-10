#!/usr/bin/env python
#  Copyright (c) 2008 Corey Goldberg (corey@goldb.org)
#
#  Create RRD

import sys
import os
import time
sys.path.append('/root/QNIB/serverfiles/usr/local/lib')
import rrd
import dbCon
import libTopology

class MYparameter(libTopology.Parameter):
    def default(self):
        # Default-Options
        self.parser.add_option("-d",
            action="count",
            dest="debug",
            help="increases debug [default:None, -d:1, -ddd: 3]")
        self.parser.add_option("-c", dest="cfgfile",
                    default="/root/QNIB/serverfiles/usr/local/etc/default.cfg",
                    action = "store", help = "Configfile (default: %default)")


def main(argv=None):
    opt = MYparameter(argv)
    
    datab = dbCon.dbCon(opt)
    
    
    
    query = """SELECT DISTINCT n_name, p_ext
                FROM ports NATURAL JOIN nodes
                ORDER BY n_name,p_ext;"""
    res = datab.sel(query)
    data = {}
    for row in res:
        (n_name, p_ext) = row
        if n_name not in data.keys():
            data[n_name] = []
        data[n_name].append(p_ext)
    
    for node, ports in data.items():
        for p_ext in ports:
            my_rrd = rrd.RRD(node, p_ext)
            my_rrd.html5(45)
        
        
     
    
if __name__ == "__main__":
    main()
