#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Bibliotheken laden
import re 
import os
import sys
import commands
import time
import random
import ConfigParser
from optparse import OptionParser

sys.path.append('/root/QNIB/serverfiles/usr/local/lib/')
#from pysqlite2 import dbapi2 as sqlite3
import sqlite3
import libTopology
import dbCon

class config(object):
    def __init__(self, cfgfiles, opt):
        self.opt = opt
        self.deb = opt.debug
        self.cfg = ConfigParser.ConfigParser()
        self.cfgfiles = cfgfiles
    def eval(self):
        for cfgfile in self.cfgfiles:
            self.cfg.read(cfgfile)
            self.data = {}
            for section in self.cfg.sections():
                self.data[section] = {}
                for form in self.cfg.options(section):
                    self.data[section][form] = {}
                    val = self.cfg.get(section, form)
                    for opt in val.split(",,"):
                        (k, v) = opt.split(";;")
                        self.data[section][form][k] = v
    def __str__(self):
        res = ""
        for section, options in self.data.items():
            res += "# %s\n" % section
            for option in options.keys():
                res += "## %s\n" % option
        return res
    def get(self, section, option=""):
        if option == "":  return self.data[section]
        else:           return self.data[section][option]

    
def main(argv=None):
    # Parameter
    options = libTopology.Parameter(argv)
    options.check()
    
    log = libTopology.logC("/var/log/create_netgrph.log")
    
    cfg = config([options.netcfg, options.topocfg], options)
    cfg.eval()
    
    db = dbCon.dbCon(options)
    try: os.remove("/tmp/topology.db")
    except: pass
    cDB = libTopology.cacheDB(options, cfg, db, log,"/tmp/topology.db")
    #cDB = libTopology.cacheDB(options, cfg, db, log)
    
    # init with true clones topology also
    cDB.init(True)
    ## Los gehts
    topo = libTopology.myTopo(cDB,options,cfg,log)
    # Create Topology
    topo.create("plain")
    topo.svg()
    
    # No Backup needed, we just use the DB
    #cDB.bkpDat()
    print log
        
if __name__ == "__main__":
    main()