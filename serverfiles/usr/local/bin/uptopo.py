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


class graph(object):
    def __init__(self, cDB, options):
        self.opt = options
        self.cDB = cDB
        self.links = set([])
    def deb(self,msg,deb=3):
        if self.opt.debug>=deb:
            print "graph> %s" % msg
    def evalSystems(self):
        seenSys = []
        systemsNext = []
        switches = []
        systems = self.cDB.getSystems()
        changedSids = []
        while True:
            if len(systems)==0: break
            system = systems.pop()
            
            ## Wenn der Knoten ein Chassis-Knoten ist, dann...
            if system.isChassis():
                # gehen erstmal alle Lampen an, stimmt das ueberhaupt noch?
                raise IOError("sure thats working?")
                #print "## Chassis: ",system, str(self.cDB.isEdgeSwitch(system.s_id))
                # Infos setzen, falls noch nicht getan
                back = self.cDB.getSystem(system.s_id)
                # Erstellen wir Stelv-Knoten
                chassis_sys = self.cDB.addChassis(system)
                # Loesche alle Knoten aus meiner Systems-Liste, die dem Chassis angehoeren
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
            elif system.nt_name=="switch":
                switches.append(system)
                self.deb("Appende Switch: %s" % system,1)
            else:
                systemsNext.append(system)
        
        while True:
            if len(systemsNext)==0 and len(switches)==0: break
            if len(switches)!=0:
                system = switches.pop()
                self.deb("Poppe Switch: %s" % system,2)
            else:
                system = systemsNext.pop()
            #system.alterEdgesSid(changedSids)
            if system.nt_name=='switch' and self.cDB.isEdgeSwitch(system.s_id):
                self.deb("## Edge: %s | %s" % (system, str(self.cDB.isEdgeSwitch(system.s_id))),1)
                sg_id = self.cDB.addCluster(system.name)
                gn_id = self.cDB.sys2SgNode(system,sg_id)
                childs = self.cDB.getSysChilds(system.s_id)
                for child in childs:
                    if child.s_id == system.s_id: continue
                    if not child.isSwitch(): 
                        try: systemsNext.remove(child)
                        except ValueError,e:
                            print """ Child '%s' nicht in Liste der systeme... Juckt mich das? """ % child
                            print "Ich glaube ja! ENDE!"
                            sys.exit()
                        self.deb("""## Switch hat Child: %s""" % child,1)
                        gn_id = self.cDB.sys2SgNode(child,sg_id)
                    elif not self.cDB.isEdgeSwitch(child.s_id):
                        # Ja, was machen wir da?
                        self.deb("## Kein Edge: %s" % child,1)
                        gn_id = self.cDB.sys2SgNode(child)
            else:
                """ Es handelt sich nicht um ein geclusterten Knoten """
                self.deb("## Child: %s"%system,1)
                gn_id = self.cDB.sys2SgNode(system)
            for edge in system.edges:
                self.links.add(edge)
        for link in self.links:
            link.setSids(changedSids)
            try:
                self.cDB.addGSysEdge(link.src_sId,link.dst_sId)
            except:
                print link, changedSids
                raise IOError
    def addNode(self, node):
        pass

class graphEdge(object):
    def __init__(self,cDB, l_id, s_p_lid, s_p_id, s_p_int, s_n_id, circle, d_n_id, d_p_int, d_p_id, d_p_lid):
        self.cDB    = cDB
        self.l_id   = l_id
        self.s_p_lid   = s_p_lid
        self.s_p_id  = s_p_id
        self.s_p_int  = s_p_int
        self.s_n_id   = s_n_id
        self.circle = circle
        self.d_n_id   = d_n_id
        self.d_p_int  = d_p_int
        self.d_p_id  = d_p_id
        self.d_p_lid   = d_p_lid
        query = "SELECT DISTINCT s_id FROM systems NATURAL JOIN nodes WHERE n_id='%s'" % s_n_id
        res = self.cDB.selOne(query)
        self.src_sId = res[0]
        query = "SELECT DISTINCT s_id FROM systems NATURAL JOIN nodes WHERE n_id='%s'" % d_n_id
        res = self.cDB.selOne(query)
        self.dst_sId = res[0]
    def setGnId(self,gn_id):
        self.gn_id  = gn_id
    def __eq__(self, other):
        return self.l_id == other.l_lid
    def __str__(self):
        return "%s:%s" % (self.src_sId,self.dst_sId)
    def setSid(self,old,new):
        if self.src_sId==old:
            self.src_sId=new
        elif self.dst_sId==old:
            self.dst_sId=new
    def setSids(self,ch_sids):
        for old,new in ch_sids:
            self.setSid(old,new)
    def isExternal(self):
        query = """SELECT c_id FROM ports NATURAL JOIN nodes
                                        NATURAL JOIN systems
                             WHERE p_id='%s' or p_id='%s'""" % \
                                        (self.s_p_id,self.d_p_id)
        res = self.cDB.sel(query)
        acc = set([])
        for row in res:
            acc.add(row[0])
        return len(acc)==2

class graphSys(object):
    def __init__(self, name):
        self.name = name
        self.s_id       = 0
        self.c_id       = 0
        self.s_guid     = 0
        self.cir_cnt    = 0
        self.sw_cnt     = 0
        self.extSw_cnt  = 0
        self.comp_cnt   = 0
        self.edges      = set([])
        self.backSet    = False
    def __eq__(self, other):
        return self.s_id == other.s_id
    def setNtName(self, nt_name):
        self.nt_name       = nt_name
    def setOpts(self, s_id, s_guid):
        self.s_id       = s_id
        self.s_guid     = s_guid
    def drainSys(self,victim):
        acc = []
        for edge in victim.edges:
            if edge.isExternal():
                edge.setSid(victim.s_id,self.s_id)
                acc.append((victim.s_id,self.s_id))
                self.edges.add(edge)
        self.extSw_cnt  += victim.extSw_cnt
        self.sw_cnt     += victim.extSw_cnt
        self.cir_cnt    += victim.cir_cnt
        return acc
    def alterEdgesSid(self,ch_sids):
        for edge in self.edges:
            edge.setSids(ch_sids)
    def setChassisId(self, c_id):
        if c_id!='None':
            self.c_id       = c_id
    def setLinkList(self, back):
        if self.backSet: return
        self.backSet    = True
        ## Wenn ich Src der Links bin
        if self.s_id==back['s_s_id']:
            #...dann schnapp ich mir die Prefixe s_
            for key,val in back.items():
                m = re.match("s_(.*)",key)
                if m:
                    self.__dict__[m.group(1)] = val
        elif self.s_id==back['d_s_id']:
            #...andernfalls d_
            for key,val in back.items():
                m = re.match("d_(.*)",key)
                if m:
                    self.__dict__[m.group(1)] = val
    def setCnts(self, cir_cnt, sw_cnt, extSw_cnt, comp_cnt):
        self.cir_cnt = cir_cnt
        self.sw_cnt  = sw_cnt
        self.extSw_cnt = extSw_cnt
        self.comp_cnt = comp_cnt
    def addEdge(self, edge):
        self.edges.add(edge)
    def __str__(self):
        res = "%-20s (Cir:%-2s|cId:%s|sId:%-4s|Sw:%-2s|eSw:%-2s|Comp:%-2s)" % (self.name, self.cir_cnt, self.c_id,self.s_id, self.sw_cnt, self.extSw_cnt, self.comp_cnt)
        return res
    def createNode(self):
        self.node = pydot.Node(self.name, label=self.name)
    def isChassis(self):
        return self.c_id!=0
    def isSwitch(self):
        return self.nt_name=="switch"
    
def eval_topo(options,db,cfg,log):
    
    if False:
        try: os.remove("/tmp/topology.db")
        except: pass
        cDB = libTopology.cacheDB(options, cfg, db, log,"/tmp/topology.db")
    else:
        cDB = libTopology.cacheDB(options, cfg, db, log)
    
    cDB.init()
    ## Los gehts
    G = graph(cDB,options)
    G.evalSystems()

    topo = libTopology.myTopo(cDB,options,cfg,log)
    topo.create(True)
    topo.fixPositions()
    
    cDB.bkpDat()

def gui(qnib,opt):
    from qnib_control import logC, log_entry
    
    db = dbCon.dbCon(opt)
    
    logE = log_entry("Exec uptopo")
    qnib.addLog(logE)
    
    cfg = libTopology.config([opt.cfgfile,],opt)
    cfg.eval()
    log = logC(opt,qnib)
    eval_topo(opt, db, cfg, log)
    
    logE.set_status(log.get_status())
    qnib.refresh_log()
    
    #db.close("eval_topo")

def main(argv=None):
    options = libTopology.Parameter(argv)
    options.check()
    
    db = dbCon.dbCon(opt)
    
    cfg = config([options.cfgfile,],options)
    cfg.eval()
    log = libTopology.logC(options, "/var/log/uptopo.log")
    eval_topo(options, db, cfg, log)
    
    #db.close("eval_topo")
    
    
if __name__ == "__main__":
    main()
