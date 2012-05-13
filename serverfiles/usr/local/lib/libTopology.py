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

# Bibliotheken laden
import re, os, sys, commands,time, random
import ConfigParser
from optparse import OptionParser

sys.path.append('/root/QNIB/usr/local/lib/')

import sqlite3
import uptopo 


def all(iterable):
    for element in iterable:
        if not element:
            return False
    return True


def any(iterable):
    for element in iterable:
        if element:
            return True
    return False


class log_c(object):
    def __init__(self, opt, log_file=None):
        self.opt = opt
        self.log_file = log_file
        self.statusTXT = ""
        self.perfTXT = ""
        self.retEC = 0
        self.s = {}
        self.res = {}

    def addPerf(self,key,val):
        self.perfTXT    += "%s=%s, " % (key,val)
        if val!=0:
            self.statusTXT  += "%sms %s, " % (val,key)

    def __str__(self):
        if   self.retEC == 0:
            retTXT = "OK"
        elif self.retEC == 1:
            retTXT = "WARN"
        elif self.retEC == 2:
            retTXT = "CRIT"
        retTXT += " - %s | %s" % (self.statusTXT, self.perfTXT)
        # perfdata
        if self.log_file:
            fd = open(self.log_file, "a")
            fd.write("%s\n" % retTXT)
            fd.close()
        return retTXT

    def getEC(self):
        return self.retEC

    def start(self, stat):
        if not self.res.has_key(stat):
            self.res[stat] = 0
        self.s[stat] = time.time()

    def end(self, stat):
        e = time.time()
        self.res[stat] += int((e - self.s[stat]) * 1000)
        self.s[stat] = 0

    def finish(self, stat):
        self.addPerf(stat, self.res[stat])
        self.res[stat] = 0

    def debug(self, msg, deb=3):
        if self.opt.debug >= deb:
            print msg


class parseObj(object):
    def __init__(self, db, opt, cfg, allGuids):
        self.rDB = db
        self.opt = opt
        self.cfg = cfg
        self.allGuids = allGuids
        self.name = False
        self.id = self.__repr__().split("at ")[1][-5:-1]

    def setName(self,name):
        self.hostPat = self.cfg.get("hostpat")
        self.name = name
        self.evalName()

    def evalName(self):
        #IN: Hostname
        #OUT: name,Type
        reg = "(%s)" % "|".join(self.hostPat.keys())
        mat = re.match(reg, self. name, re.I)
        if mat:
            for reg in self.hostPat.keys():
                mat = re.match("^%s$" % reg, self.name, re.I)
                if mat:
                    if self.hostPat[reg].has_key('regname'):
                        # Regname formatiert die groups des regex neu
                        # X,Y sind platzhalter fuer die jeweiligen Matches
                        # Bei X wird die aktuelle Gruppe eingetragen
                        # Y wird ausgelassen, z.B. wenn man oder matched '(spine|line)' 
                        regname = self.hostPat[reg]['regname']
                        res = ""
                        c = 1
                        for x in regname:
                            if x == "X":
                                res += mat.group(c)
                                c += 1
                            elif x == "%":
                                res += self.lid
                            elif x == "Y":
                                c += 1
                            else:
                                res += x
                        self.name = res
                    if self.hostPat[reg].has_key('type'):
                        self.type = self.hostPat[reg]['type']
                        if type(self) is parseNode:
                            self.nt_id = self.rDB.getIns_ID('nodetypes', "nt_name='%s'" % self.type, ['nt_name'], [self.type], self.opt.debug)
                    if self.hostPat[reg].has_key('name'):
                        self.name = self.hostPat[reg]['name']
                    if self.hostPat[reg].has_key('short'):
                        self.name = "%s%s" % (self.hostPat[reg]['short'], mat.group(2))

    def setLid(self,lid):
        self.lid = str(lid)

    def getLids(self):
        if self.__dict__.has_key("lid"):
            return set([self.lid])
        else:
            return set([])

    def setGuid(self,guid):
        if guid != '':
            self.guid = guid
            if not self.allGuids.has_key(guid):
                if not re.match("[0-9a-z]+", guid, re.I):
                    print "GUID '%s' does not match GUID-Form" % guid
                    sys.exit(2)
                self.allGuids[guid] = self
    def evalGuid(self,guids):
        if self.guid in guids.keys():
            self.name = guids[self.guid]['name']
    def deb(self,msg,typ,deb):
        if typ=='p' and self.opt.parse and self.opt.debug>=deb:
            print msg
        elif typ=='l' and self.opt.links and self.opt.debug>=deb:
            print msg

class parseSystem(parseObj):
    def __init__(self,db,opt,cfg,allGuids):
        parseObj.__init__(self,db,opt,cfg,allGuids)
        self.c_id = None
    def setGuid(self,guid):
        parseObj.setGuid(self,guid)
        self.evalGuid()
        self.insDB()
    def insDB(self):
        if self.name:
            self.s_id = self.rDB.getIns_ID('systems',"s_guid='%s' AND s_name='%s'" % (self.guid,self.name),['s_guid','s_name'], [self.guid,self.name],self.opt.debug)
        else:
            self.s_id = self.rDB.getIns_ID('systems',"s_guid='%s'" % self.guid,['s_guid',], [self.guid,],self.opt.debug)
    def setChassisId(self,c_id):
        self.c_id = c_id
        query = "UPDATE systems SET c_id='%s' WHERE s_id='%s'" % (self.c_id,self.s_id)
        self.rDB.exe(query)
    def setChassisNr(self,c_nr):
        query = "SELECT c_id FROM chassis WHERE c_nr='%s'" % c_nr
        res = self.rDB.selOne(query)
        c_id = res[0]
        self.setChassisId(c_id)
    def evalGuid(self):
        guids = {} #self.cfg.get('sysimgguids')
        parseObj.evalGuid(self,guids)
    def __str__(self):
        return "%s[%s]%s" % (self.name,self.guid[-5:].self.id)

class parsePort(parseObj):
    def __init__(self,db,opt,cfg,allGuids):
        parseObj.__init__(self,db,opt,cfg,allGuids)
        self.p_int   = 0
        self.p_ext   = 0
        self.lid   = 0
        self.n_id    = 0
        self.rDB = db
    def setPNr(self,p_int):
        self.p_int   = p_int
        if self.p_ext==0:
            self.p_ext   = p_int
    def setExtPNr(self,p_ext):
        self.p_ext   = p_ext
    def setNid(self,n_id):
        self.n_id = str(n_id)
    def setGuid(self,guid):
        self.guid = guid
    def insDB(self):
        if self.guid=='':
            # Wenn es sich um einen Switchport handelt, dann bekommt der Port die pseudo-GUID <NODEGUID[-10:]>abba<PORT>
            # Diese sollte recht fix sein.
            nodeguid = self.rDB.selNodeGUID(self.n_id)
            self.guid = "%sabba%s" % (nodeguid,self.p_int)
        self.p_id = self.rDB.upsertPort(self)
    def __str__(self):
        res = "i%sp%se%sl%sn%s" % (self.p_id,self.p_int,self.p_ext,self.lid,self.n_id)
        return res

class edgeClass(object):
    def __init__(self, opt, rDB, cfg, log):
        self.cfg = cfg
        self.opt = opt
        self.rDB = rDB
        self.log = log

    def setInfo(self, row, graph):
        (self.src_gnid, self.src_name, self.dst_gnid, self.dst_name) = row
        if graph != None:
            print graph
            self.perfcache = self.rDB.getLinkPerf(self.src_name, self.dst_name)
        self.edgeOpts = {}

    def __str__(self):
        res = []
        for k,v in self.__dict__.items():
            if k in ('cfg','db','opt'): continue
            res.append("%s=%s" % (k,v))
        return "//".join(res)

    def getEdgeStr(self, graph):
        self.opts = "["
        if graph != None:
            self.getEdgeStrByGraph(graph)
        self.opts += "]"
        if self.opts != "[]":
            return "\"%s\" -> \"%s\" %s;" % \
                    (self.src_name, self.dst_name, self.opts)
        else:
            return "\"%s\" -> \"%s\";" % (self.src_name, self.dst_name)

    def getEdgeStrByGraph(self, graph):
        # Posisiton brauchen wir immer
        if graph == "perf":
            self.setPerfInfo()
        elif graph == "plain":
            self.setTopoInfo()
        else:
            self.opts += ' arrowhead=\"none\"'

    def setTopoInfo(self):
        self.opts += ' dir=\"none\"'
        if self.perfcache['width']!=4:
            self.opts += ' color=\"red\"'
            query = ""

    def setPerfInfo(self):
        (xmit, rcv, max_perf) = (self.perfcache['xmit_data'],self.perfcache['rcv_data'], self.perfcache['max_data'])
        xmit_rate = int(float(xmit)*1000/max_perf)
        rcv_rate = int(float(rcv)*1000/max_perf)
        if xmit_rate>0 and rcv_rate>0:
            color = fancy_color(xmit_rate,rcv_rate)
            self.opts += ' dir=\"both\", color=%s' % color
        elif xmit_rate>0:
            color = fancy_color1(xmit_rate)
            self.opts += ' dir=\"forward\", color=%s' % color
        elif rcv_rate>0:
            color = fancy_color1(rcv_rate)
            self.opts += ' dir=\"back\", color=%s' % color
        else:
            self.opts += ' dir=\"none\"'

    def setInTopo(self):
        query = "UPDATE g_edges SET in_topo='t' WHERE ge_src_gnid='%s' AND ge_dst_gnid='%s'" % (self.src_gnid,self.dst_gnid)
        self.rDB.ins(query)


class parseNode(parseObj):
    def __init__(self, db, opt, cfg, allGuids):
        parseObj.__init__(self, db, opt, cfg, allGuids)
        self.ports = {}
        self.nLinks = {}
        self.seen = False
        self.circle = False
        self.sw_cnt = 0
        self.extSw_cnt = 0
        self.comp_cnt = 0

    def addLink(self, dst, links, toDst=True):
        self.deb("Adde '%s' zu links von '%s'" % \
                 ([link.__str__() for link in links], dst.name), 'l', 2)
        if self.nLinks.has_key(dst):
            self.deb("Zusaetzlicher Link von '%s' nach '%s'" % \
                     (self.name, dst.name), 'l', 2)
            s = set(links)
            try:
                self.nLinks[dst] |= s
            except:
                print type(self.nLinks[dst]), self.nLinks[dst]
                sys.exit()
        else:
            self.deb("Neuer Link von '%s' nach '%s'" % \
                     (self.name, dst.name), 'l', 3)
            s = set(links)
            self.nLinks[dst] = s
        if toDst:
            dst.addLink(self, links, False)

    def setSys(self, system):
        self.system = system
        self.s_id = system.s_id

    def setGuid(self, guid):
        parseObj.setGuid(self,guid)
        self.evalGuid()
        self.insDB()

    def insDB(self):
        # Knoten wird guid angelegt
        if self.name:
            self.n_id = self.rDB.getIns_ID('nodes',"n_guid='%s' AND n_name='%s'" % (self.guid,self.name),['n_guid','n_name'], [self.guid,self.name],self.opt.debug)
        else:
            self.n_id = self.rDB.getIns_ID('nodes',"n_guid='%s'" % (self.guid),['n_guid',], [self.guid,],self.opt.debug)

    def createPort(self,pnr,pguid,lid):
        port = parsePort(self.rDB,self.opt,self.cfg,self.allGuids)
        port.setPNr(pnr)
        port.setNid(self.n_id)
        port.setGuid(pguid)
        port.setLid(lid)
        # Hier wird der Port in die DB eingetragen, daher am Ende
        port.insDB()
        self.ports[pnr] = port
        return port

    def getPort(self,pnr):
        return self.ports[pnr]

    def setPortLid(self,pnr,lid):
        self.ports[pnr].lid = lid

    def evalGuid(self):
        guids = {} #self.cfg.get('nodeguids')
        parseObj.evalGuid(self,guids)

    def updateCnt(self):
        query = "UPDATE nodes SET"
        query += " sw_cnt='%s', extSw_cnt='%s', comp_cnt='%s'" % (self.sw_cnt,self.extSw_cnt,self.comp_cnt)
        query += " WHERE n_id='%s'" % self.n_id
        self.deb(query,"p",2)
        self.rDB.exe(query)

    def getLids(self):
        res = set([])
        for port in self.ports.values():
            res |= port.getLids()
        return res

    def updateDB(self):
        query = "UPDATE nodes SET"
        try:    name = self.name
        except: raise IOError("Name muessen mer schon haben!")
        else:   query += " n_name='%s'" % name
        try:    s_id = self.s_id
        except: pass
        else:   query += ",s_id='%s'" % s_id
        try:    nt_id = self.nt_id
        except: pass
        else:   query += ",nt_id='%s'" % nt_id
        try:    n_id  = self.n_id
        except: raise IOError("Ohne n_id sehen wir alt aus!")
        else:   query += " WHERE n_id='%s'" % n_id
        self.deb(query,"p",2)
        self.rDB.exe(query)

    def setType(self,typ):
        self.nt_id = self.rDB.getIns_ID('nodetypes',"nt_name='%s'" % typ,['nt_name',], [typ,],self.opt.debug)
        self.type = typ

    def setSwitch(self):
        self.setType('switch')

    def setHost(self):
        self.setType('host')

    def isType(self,types):
        return self.type in types

    def isSwitch(self):
        return self.isType(['switch', 'root'])

    def getIntSwLink(self,path=[]):
        freshLinks = [x for x in self.links.values() if (x.isInterswitch() and not x.seen and x not in path)]
        try:
            res= freshLinks.pop()
        except IndexError:
            return None
        return res

    def createCircle(self,obj):
        cir_id = self.rDB.getIns_ID('circles',"n_id='%s' AND pathhex='%s'" % (str(self.n_id),obj),['n_id','pathhex'], [str(self.n_id),obj],self.opt.debug)
        return cir_id

    def setCircleLinks(self,cir_id,prv):
        self.deb("!!Kreisknoten: %s" % self,'l',1)
        for node,links in self.nLinks.items():
            if node==prv: 
                for link in links:
                    link.setCircle(cir_id)

    def __str__(self):
        res = "%s[%s]%s" % (self.name,self.id,self.guid[-3:])
        if self.__dict__.has_key("s_id"):
            res += "(%s)" % self.s_id
        res += "."
        if self.seen:   res += "S"
        else:           res += "_"
        if self.circle: res += "C"
        else:           res += "_"
        return res


class parseLink(parseObj):
    def __init__(self,db,opt,cfg):
        self.rDB     = db
        self.opt    = opt
        self.cfg    = cfg
    def setOpts(self,sNode,sPort,dNode,dPort):
        if dNode.nLinks.has_key(sNode):
            # Wenn das Gegenüber schon angeschaut wurde, dann sind _alle_ Links schon evaluiert
            # Es koennen nicht mehr Links hinzukommen, da der Gegenpart schon fertig geparst sein muss (oder?)
            res = dNode.nLinks[sNode]
            #sNode.addLink(dNode,res)
            return res
        self.src_pId = self.rDB.getPID(sNode,sPort)
        self.src     = (sNode,sPort)
        try:
            self.dst_pId = self.rDB.getPID(dNode,dPort)
            self.dst     = (dNode,dPort)
        except IOError,e:
            if sNode.name=="A1":
                print "IOError self.rDB.getPID(dNode,dPort): %s" % e
                sys.exit()
            return None
        self.seen    = False
        self.circle  = False
        self.reverse = False
        self.id      = self.__repr__().split("at ")[1][-5:-1]
        if not sNode.nLinks.has_key(dNode):
            sNode.addLink(dNode,[self,])
        return self
    def setLinkID(self,l_id):
        self.l_id = l_id
    def __eq__(self,other):
        return self.nodes==other.nodes and self.ports==other.ports
    def isInterswitch(self):
        res = all([x.type=='switch' for x in self.nodes])
        return res
    def orient(self,src):
        if self.list[0].name==src.name:
            self.dst = self.list[1]
        else:
            self.dst = self.list[0]
    def hasNode(self,node):
        self.deb("%s in %s?" % (node, ",".join([x.__str__() for x in self.nodes])),'p',2)
        return node in self.nodes
    def __str__(self):
        res = []
        t = "%s<%s>%s" % (self.src[0].name,self.id,self.dst[0].name)
        res.append(t)
        if self.seen: res.append("*")
        return "".join(res)
    def setCircle(self,cir_id):
        self.deb("Kreiskante: %s" % self,'l',1)
        self.circle = True
        self.rDB.linkSetCircle(self.src,self.dst,cir_id)
    def updateDB(self):
        pass


class evalPath(object):
    def __init__(self,opt,node):
        self.opt = opt
        self.path = []
        self.nodes = [node,]
        self.circle = False
    def deb(self,msg,deb):
        if self.opt.links and self.opt.debug>=deb:
            print msg
    def foundCircle(self):
        self.circle = True
        self.path.append(None)
    def flushCircle(self,node):
        # Letzter Link is auf jeden Fall Kreiskante
        link = self.path.pop()
        link.setCircle()
        self.deb("Kreiskante: %s +" % link,1)
        while True:
            try: link = self.path.pop()
            except IndexError: break
            if type(link) is parseLink and not link.hasNode(node):
                self.deb("Kreiskante: %s -" % link,1)
                link.setCircle()
            else:
                # Wenn der doppelt gefundene Knoten erreicht wurde, steigen wir aus
                break
    def addLink(self,link,src):
        link.seen = True
        link.orient(src)
        self.path.append(link)
    def eval(self):
        dst = self.path[-1].dst
        if not dst.isSwitch:
            self.deb("Kein Switch: %s" % dst.name,1)
        elif dst.name in self.nodes:
            self.deb("Schon besucht: %s" % dst.name,1)
            self.flushCircle(dst)
        else:
            # Haben wir den Knoten schon gesehen?
            self.nodes.append(dst.name)
            link = dst.getIntSwLink(self.path)
            if type(link) is not parseLink: return
            self.deb("Beschaue innen Link: %s" % link,1)
            # Nun sind wir sicher, dass es sich um einen interswitch-Link handelt
            if link.circle:
                if self.circle:
                    # Bei der zweiten ist der Pfad bis zur ersten ebenfalls Teil eines Kreises
                    self.flushCircle()
                    # Reset des Pfades
                    self.path = []
                    self.circle = False
                    # Wieder zurueck zur Link-Schleife
                    raise IOError("Kreis gefunden! Was nu?")
                    sys.exit()
                # Wenn es die erste Kreiskante ist: weiter
                self.foundCircle()
            # Link dem Pfad hinzufuegen
            self.addLink(link,dst)
            # Rekursiv aufrufen
            self.eval()


class thePath(object):
    def __init__(self,opt):
        self.opt            = opt
        self.links          = set([])
        self.nodes          = []
    def __str__(self):
        res = ""
        res += ">>".join([x.name for x in self.nodes])
        return res
    def addLinks(self,links):
        for link in links:
            self.deb("Adde %s" % link,3)
            self.links.add(link)
    def addNode(self,node):
        self.deb("Adde %s" % node,0)
        self.nodes.append(node)
    def linkIn(self,linkList):
        if 0==len(self.links): return False
        for link in linkList:
            if link in self.links: return True
        return False 
    def nodeIn(self,node):
        return (node in self.nodes)
    def rmLink(self,links):
        for link in links:
            self.links.remove(link)
    def rmNode(self,node):
        node.updateCnt()
        self.deb("Rm %s" % node,0)
        self.nodes.remove(node)
    def flush(self,node):
        ns = list(self.nodes)
        # Die Knoten in der Liste 'ns' werden nach Links zum Kreisvorgänger abgesucht
        # Initial ist der Endknoten der Vorgänger
        prv = node
        cir_id = node.createCircle(self.__str__()[:56])
        while True:
            n = ns.pop()
            #n.setCircle(node)
            n.setCircleLinks(cir_id,prv)
            prv = n
            if n==node: break
    def deb(self,msg,deb):
        if self.opt.links and self.opt.debug>=deb:
            print msg


def fancy_color1(val):
    color = {
        0:"#8080ff",
        1:"#ae80ff",
        2:"#c580ff",
        3:"#dc80ff",
        4:"#f380ff",
        5:"#ff80f3",
        6:"#ff80dc",
        7:"#ff80c5",
        8:"#ff80ae",
        9:"#ff8097",
        10:"#ff8080", 
    }
    return "\"%s\"" % (color[(min(val,100)/10)])

def fancy_color(val1, val2):
    color = {
        0:"#8080ff",
        1:"#ae80ff",
        2:"#c580ff",
        3:"#dc80ff",
        4:"#f380ff",
        5:"#ff80f3",
        6:"#ff80dc",
        7:"#ff80c5",
        8:"#ff80ae",
        9:"#ff8097",
        10:"#ff8080", 
    }
    return "\"%s:%s\"" % (color[(min(val1,100)/10)],color[(min(100,val2)/10)])


class node(object):
    def __str__(self):
        res = "name:%-5s || %s" % (self.name,self.nodeOpts)
        return res

    def setNodeInfo(self, row, graph='plain'):
        (sg_id, c_id, s_id, n_id,
         n_status, gn_id, gn_name, gn_shape) = row
        self.sg_id = sg_id
        self.c_id = c_id
        self.s_id = s_id
        self.n_id = n_id
        self.n_status = n_status
        self.gn_id = gn_id
        self.nodeOpts['shape'] = gn_shape
        query = "SELECT gno_key, gno_val FROM gn_options WHERE gn_id='%s'" % gn_id
        res = self.cDB.sel(query)
        for row in res:
            (key, val) = row
            self.nodeOpts[key] = val
        statQ = "SELECT count(s_id) FROM systems WHERE s_rev='%s'" % s_id
        res = self.cDB.selOne(statQ)
        s_rev = res[0]
        if graph == 'plain':
            self.nodeOpts['tooltip'] = ""
        self.nodeOpts['URL'] = "\"index.php?map=root_perf&node_details=%s\"" % \
                                self.name

        if not self.nodeOpts['shape']:
            if self.nt_name == 'switch':
                self.nodeOpts['shape'] = 'octagon'
            elif self.nt_name == 'host':
                self.nodeOpts['shape'] = 'none'
        # Eval states
        if self.n_status == "fail":
                self.nodeOpts['fontcolor'] = 'red'
        elif self.n_status == "new":
                self.nodeOpts['fontcolor'] = 'darkgreen'
                self.nodeOpts['style'] = 'filled'
        elif self.n_status == "nok":
                self.nodeOpts['fontcolor']  = 'blue'
        elif self.n_status == "deg":
            if self.nt_name == 'switch':
                self.nodeOpts['fontcolor'] = 'orange'
            else:
                self.nodeOpts['fontcolor'] = 'red'
        if graph == 'perf' and self.nt_name in ('switch', 'root'):
            # FIXME: link performance is cDB, locality cDB -> inconsistent
            query = "SELECT * FROM getLocality('%s')" % gn_name
            res = rDB.selOne(query)
            if len(res) >= 1:
                (downRes, upRes, upIn, downOut, upOut, downIn) = res
                (upin_downout, upout_downin) = res[:2]
                locality = max(upin_downout, upout_downin)
                self.nodeOpts['style'] = 'filled'
                self.nodeOpts['fillcolor'] = fancy_color(upin_downout, upout_downin)
                self.nodeOpts['tooltip'] = "\"upIn/downOut:%s%% || upOut/downIn:%s%% \"" % (upin_downout, upout_downin)

    def getNodeOpts(self):
        opts = "["
        for k, v in self.nodeOpts.items():
            if v != "" and v != None:
                opts += "%s=%s " % (k, v)
        opts += "]"
        if opts != "[]":
            return opts
        else:
            return ""

    def setNodeOpts(self, key, val):
        self.nodeOpts[key] = val

    def colorize(self,val,maxi):
        try:    val = float(val)*100/maxi
        except: return None
        col ={
            10:"#11FF11",
            20:"#58FF11",
            30:"#88FF11",
            40:"#B8FF10",
            50:"#E7FF10",
            60:"#FFE60E",
            70:"#FF990A",
            80:"#FF6606",
            90:"#FF3303",
            100:"#FF0000",
        }
        keys = col.keys()
        keys.sort()
        for k in keys:
            if int(val)<=k:
                c = col[k]
                break
        else: c = col[100]
        return c

    def setInTopo(self):
        query = "UPDATE g_nodes SET in_topo='t' WHERE gn_id='%s'" % self.gn_id
        self.cDB.ins(query)


class nodeNid(node):
    """ Node class based on node_ids, this will lead to a graph that includes all ASICs"""
    def __init__(self,opt,db,cfg,n_id,IamIn=True):
        raise IOError("wollte nicht in nodeNid")
        self.IamIn = IamIn
        self.cfg = cfg
        self.opt = opt
        self.rDB = db

        select = "s_id,s_guid,s_name,c_id,n_id,n_name,n_guid,nt_id,nt_name,in_topo,edge_eval,in_sg"
        if n_id!=None:
            query = "SELECT %s FROM systems NATURAL JOIN nodes NATURAL JOIN nodetypes WHERE n_id='%s'" % (select,n_id)
        else:
            root = cfg.get("graphviz","root")['name']
            query = "SELECT %s FROM systems NATURAL JOIN nodes NATURAL JOIN nodetypes WHERE s_name REGEXP '%s' OR n_name REGEXP '%s'" % (select,root,root)
            self.isRoot = True
        if self.opt.debug>=1: print query
        res = self.rDB.sel(query)
        (self.s_id,self.s_guid,self.s_name,self.c_id,self.n_id,self.n_name,self.n_guid,self.nt_id,self.nt_name,self.in_topo,self.edge_eval,in_sg) = res[0]
        query = "SELECT DISTINCT p_lid FROM ports WHERE n_id='%s'" % self.n_id
        if self.opt.debug>=2: print "n_name:'%s', s_name:'%s'"% (self.n_name,self.s_name)
        if self.n_name=='None' or self.n_name==None:
            self.name = self.s_name
        else:
            self.name = self.n_name
        res         = self.rDB.sel(query)
        self.lid    = res[0][0]
        self.root   = None
        self.parent = None
        self.typ    = None 
        self.nodeOpts = {
            'pos':None,
            'shape':None,
            'width':None,
            'height':None,
            }
        # Counter fuer Switch-Kinder, haben die Switchkinder keine validen Knoten,
        # so wird der Switch am Ende aus dem Graphen geschmissen
        self.showInGraph = 0
        self.children = []
        self.links = 1


class nodeGnId(node):
    """ Node class based on graphnode_ids, this will lead to a graph that only shows chassis (systems)"""
    def __init__(self, opt, cDB, rDB, cfg, gn_id, IamIn=True):
        self.IamIn = IamIn
        self.cfg = cfg
        self.opt = opt
        self.cDB = cDB
        self.rDB = rDB
        select = " s.s_id, s_guid, s_name, s.c_id, gn_id, sg_id,gn_name, gn_shape, nt_name, gn.in_topo"
        query = "SELECT DISTINCT %s FROM systems s NATURAL JOIN nodes NATURAL JOIN nodetypes JOIN g_nodes gn ON s.s_id=gn.s_id WHERE gn_id='%s'" % (select,gn_id)
        if self.opt.debug >= 2:
            print query
        res = self.cDB.sel(query)
        if len(res) == 0:
            query = """SELECT DISTINCT %s FROM systems s NATURAL JOIN nodes
                            NATURAL JOIN nodetypes
                            JOIN g_nodes gn ON s.c_id=gn.c_id
                            WHERE gn_id='%s'""" % (select, gn_id)
            res = self.cDB.sel(query)
        (self.s_id, self.s_guid, self.s_name, self.c_id, self.gn_id,
         self.sg_id, self.gn_name, self.gn_shape,
         self.nt_name, self.in_topo) = res[0]

        if self.in_topo=='f':
            self.in_topo = False
        else:
            self.in_topo = True
        self.name = self.gn_name
        self.root = None
        self.parent = None
        self.typ = None
        self.inGraph = False
        self.nodeOpts = {
            'pos':None,
            'shape':None,
            'width':None,
            'height':None,
            }
        # Counter fuer Switch-Kinder, haben die Switchkinder keine validen Knoten,
        # so wird der Switch am Ende aus dem Graphen geschmissen
        self.showInGraph = 0
        self.children = []
        self.links = 1

def colorize(val,maxi):
    try:    val = float(val)*100/maxi
    except: return None
    col ={
        10:"#11FF11",
        20:"#58FF11",
        30:"#88FF11",
        40:"#B8FF10",
        50:"#E7FF10",
        60:"#FFE60E",
        70:"#FF990A",
        80:"#FF6606",
        90:"#FF3303",
        100:"#FF0000",
    }
    keys = col.keys()
    keys.sort()
    for k in keys:
        if int(val)<=k:
            c = col[k]
            break
    else: c = col[100]
    return c

def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None


class cacheDB(object):
    def __init__(self, opt, cfg, db, log, filename=None):
        self.opt = opt
        self.cfg = cfg
        self.log = log
        self.rDB = db
        self.commitCount = 0
        self.querys = 0
        if filename is None:
            filename = ":memory:"
        sql_conn = sqlite3.connect(filename)

        sql_conn.isolation_level = "DEFERRED"
        #sql_conn.isolation_level="EXCLUSIVE"
        #sql_conn.isolation_level=None

        sql_cursor = sql_conn.cursor()

        sql_cursor.execute("PRAGMA synchronous=OFF")
        sql_cursor.execute("PRAGMA count_changes=OFF")
        sql_cursor.execute("PRAGMA journal_mode=MEMORY")
        sql_cursor.execute("PRAGMA temp_store=MEMORY")
        self.__cur = sql_cursor
        self.__con = sql_conn
        self.gnInside = False
    def deb(self,msg,deb):
        if self.opt.db and self.opt.debug>=deb:
            print "db> %s" % msg
    def init(self,topo=False):
        self.createTabs()
        self.createFunc()
        self.cloneDat(topo)
        self.enhanceTabs(topo)
        self.statesNames = self.getStatesName()
        self.stateIds = self.getStatesId()
    def createTabs(self):
        self.__cur.execute("""CREATE TABLE chassis (
                c_id INTEGER PRIMARY KEY AUTOINCREMENT,	
                c_guid varchar (32),
                c_nr integer,
                c_name varchar (255)
            );"""
            )
        self.__cur.execute("""CREATE TABLE states (
            state_id INTEGER PRIMARY KEY AUTOINCREMENT,	
            state_name VARCHAR(5)
            );"""
            )
        self.__cur.execute("""CREATE TABLE systems (
            s_id INTEGER PRIMARY KEY AUTOINCREMENT,	
            s_rev INTEGER DEFAULT 0,
            s_guid varchar (32),
            s_name varchar (255),
            s_real boolean DEFAULT 't',
            s_state_id REFERENCES states(state_id),
            c_id integer DEFAULT 0
            );""")
        self.__cur.execute("""CREATE TABLE nodetypes (
                nt_id SERIAL,
                nt_name varchar (32),
                CONSTRAINT nodetypes_pk
                    PRIMARY KEY (nt_id)
            );"""
            )
        self.__cur.execute("""CREATE TABLE nodes (
            n_id INTEGER PRIMARY KEY AUTOINCREMENT,	
            n_rev INTEGER DEFAULT 0,
            n_guid varchar (32),
            n_name varchar (255),
            n_real boolean DEFAULT 't',
            n_state_id references states(state_id),
            s_id integer references systems(s_id) ON DELETE CASCADE,
            nt_id integer references nodetypes(nt_id),
            cir_cnt integer DEFAULT 0,
            sw_cnt integer DEFAULT 0,
            extSw_cnt integer DEFAULT 0,
            comp_cnt integer DEFAULT 0
            );""")
        self.__cur.execute("""CREATE TABLE ports (
                p_id SERIAL,
                n_id integer references nodes(n_id) ON DELETE CASCADE,
                p_guid varchar (32),
                p_lid integer,
                p_int integer,
                p_ext integer,
                p_state_id REFERENCES states(state_id),
                CONSTRAINT ports_pk PRIMARY KEY (p_id),
                CONSTRAINT con1     UNIQUE (n_id,p_int)
            );"""
            )
        self.__cur.execute("""CREATE TABLE circles (
                cir_id SERIAL,
                n_id integer, -- Knoten, der es ausgeloest hat
                pathhex varchar(56),
                CONSTRAINT circles_pk PRIMARY KEY (cir_id)
            );"""
            )
        self.__cur.execute("""CREATE TABLE links (
                l_id SERIAL,
                src integer references ports(p_id) ON DELETE CASCADE,
                dst integer references ports(p_id) ON DELETE CASCADE,
                width integer,
                speed integer,
                uplink boolean DEFAULT 't',
                l_status varchar(3) DEFAULT 'new',
                circle boolean DEFAULT 'f',
                CONSTRAINT width_check CHECK (width in ('1','2','4','12')),
                CONSTRAINT links_pk PRIMARY KEY (src,dst)
            );"""
            )
        self.__cur.execute("""CREATE TABLE circles_x (
                cir_id integer,
                l_id integer,
                CONSTRAINT circles_x_pk
                    PRIMARY KEY (cir_id,l_id)
            );"""
            )
        self.__cur.execute("""CREATE TABLE perfkey_types (
                pkt_id SERIAL,
                pkt_name varchar (255),
                CONSTRAINT perfkey_type_pk
                    PRIMARY KEY (pkt_id)
            );"""
            )
        self.__cur.execute("""CREATE TABLE perfkeys (
                pk_id SERIAL,
                pk_name varchar (255),
                CONSTRAINT perfkey_pk
                    PRIMARY KEY (pk_id)
            );"""
            )
        self.__cur.execute("""CREATE TABLE perfdata (
                pd_id INTEGER PRIMARY KEY AUTOINCREMENT,
                p_id integer references ports(p_id) ON DELETE CASCADE,
                pk_id integer references perfkeys(pk_id),
                pdat_val bigint,
                pdat_time timestamp DEFAULT CURRENT_TIMESTAMP
            );"""
            )
        self.__cur.execute("""CREATE TABLE perfcache (
                pc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                p_id integer references ports(p_id) ON DELETE CASCADE,
                pk_id integer references perfkeys(pk_id),
                pc_val bigint
            );"""
            )
        self.__cur.execute("""CREATE TABLE perfhist (
                p_id integer references ports(p_id) ON DELETE CASCADE,
                pk_id integer references perfkeys(pk_id),
                pc_val bigint,
                CONSTRAINT perfhist_pk
                    PRIMARY KEY (p_id,pk_id)
            );"""
            )
        # Topology
        self.__cur.execute("""CREATE TABLE subgraphs (
                sg_id INTEGER PRIMARY KEY,
                sg_name varchar(32)
            );""")
        self.__cur.execute("""CREATE TABLE g_edges (
                -- Spine<>Line-Kanten kommen ans Ende des Graphen
                ge_id INTEGER PRIMARY KEY,
                ge_src_gnid INTEGER,
                ge_src varchar(32),
                ge_dst_gnid INTEGER,
                ge_dst varchar(32),
                in_topo boolean DEFAULT 'f'
            );"""
            )
        self.__cur.execute("""CREATE TABLE sg_options (
                sgo_id INTEGER PRIMARY KEY,
                sg_id INTEGER,
                sgo varchar(255),
                CONSTRAINT doppelcheck UNIQUE (sg_id,sgo)
            );"""
            )
        self.__cur.execute("""CREATE TABLE gn_options (
                gno_id INTEGER PRIMARY KEY,
                gn_id INTEGER,
                gno_key varchar(56),
                gno_val varchar(255),
                CONSTRAINT doppelcheck UNIQUE (gn_id,gno_key)
            );"""
            )
        self.__cur.execute("""CREATE TABLE g_nodes (
                gn_id INTEGER PRIMARY KEY,
                sg_id INTEGER REFERENCES subgraphs(sg_id) ON DELETE CASCADE,
                s_id INTEGER,
                n_id INTEGER,
                c_id INTEGER DEFAULT 0,
                gn_name varchar(64),
                gn_shape varchar(64),
                in_topo boolean DEFAULT 'f'
            );"""
            )
        self.__cur.execute("""CREATE TABLE sg_edges (
                sge_id INTEGER PRIMARY KEY,
                sg_id INTEGER REFERENCES subgraphs(sg_id) ON DELETE CASCADE,
                sge_src_gnid INTEGER REFERENCES g_nodes(gn_id),
                sge_src varchar(32),
                sge_dst_gnid INTEGER REFERENCES g_nodes(gn_id),
                sge_dst varchar(32),
                in_topo boolean DEFAULT 'f'
            );""")
        self.__cur.execute("""CREATE TABLE sg_lines (
                n_id INTEGER PRIMARY KEY,
                name varchar(32)
            );""")
        self.__cur.execute("""CREATE TABLE g_switches (
                n_id INTEGER PRIMARY KEY,
                name varchar(32)
            );""")
        # opensm
        self.__cur.execute("""CREATE TABLE traps (
                trap_id INTEGER PRIMARY KEY,
                trap_type integer,
                trap_event integer,
                trap_lid integer,
                trap_time timestamp DEFAULT CURRENT_TIMESTAMP
            );""")
        self.commit()
    def commit(self):
        self.commitCount += 1
        self.__con.commit()
    def createFunc(self):
        self.__con.create_function("REGEXP", 2, regexp)
        self.commit()
    def cloneDat(self,topo):
        self.log.start("cloneDat")
        tabs = ['chassis',
                'states',
                'systems',
                'nodetypes',
                'nodes',
                'ports',
                'perfkeys',
                'perfdata',
                'perfcache',
                'links',
                'circles',
                'circles_x',
                'traps',
                ]
        if topo:
            tabs.extend([
            'subgraphs',
            'g_edges',
            'sg_options',
            'gn_options',
            'g_nodes',
            'sg_edges',
            ])
        for tab in tabs:
            self.cloneTab(tab)
        self.log.end("cloneDat")
    def bkpDat(self):
        self.log.start("bkpDat")
        tabs = [
            'subgraphs',
            'g_edges',
            'sg_options',
            'g_nodes',
            'gn_options',
            'sg_edges',
        ]
        for tab in tabs:
            self.bkpTab(tab)
        self.log.end("bkpDat")
        self.sync()
    def sync(self):
        tabs = [
            'nodes'
        ]
        for tab in tabs:
            self.sync_tab(tab)
    def sync_tab(self, tab):
        query = "SELECT n_id, nt_id FROM %s" % tab
        res = self.sel(query)
        for row in res:
            (n_id, nt_id) = row
            upsert_query = "UPDATE nodes SET nt_id='%s' WHERE n_id='%s'" % (nt_id, n_id)
            self.rDB.exe(upsert_query)
    def bkpTab(self,tab):
        query = "SELECT * FROM %s" % tab
        res = self.sel(query)
        query = "DELETE FROM %s" % tab
        self.rDB.exe(query)
        for row in res:
            insQ = "INSERT INTO %s VALUES ('%s')" % (tab,"','".join([str(x) for x in row]))
            insQ = insQ.replace("'Null'","Null")
            insQ = insQ.replace("'None'","Null")
            try: self.rDB.ins(insQ)
            except UnicodeDecodeError,e:
                print insQ
                self.deb(e,2)
                raise IOError
    def cloneTab(self,tab):
        query = "SELECT * FROM %s" % tab
        self.deb(query,3)
        res = self.rDB.sel(query)
        for row in res:
            insQ = "INSERT INTO %s VALUES ('%s')" % (tab,"','".join([str(x) for x in row]))
            self.deb(insQ,3)
            try: self.ins(insQ)
            except sqlite3.OperationalError,e:
                print insQ
                print e
                raise sqlite3.OperationalError            
    def enhanceTabs(self,topo):
        self.__cur.execute("""ALTER TABLE nodes ADD COLUMN in_topo boolean DEFAULT 'f';""")
        self.__cur.execute("""ALTER TABLE nodes ADD COLUMN edge_eval boolean DEFAULT 'f';""")
        self.__cur.execute("""ALTER TABLE nodes ADD COLUMN in_sg boolean DEFAULT 'f';""")
        if not topo:
            self.__cur.execute("INSERT INTO subgraphs VALUES ('0','empty');")
            # States 
            self.__cur.execute("INSERT INTO states (state_name) VALUES ('new');")
            self.__cur.execute("INSERT INTO states (state_name) VALUES ('chk');")
            self.__cur.execute("INSERT INTO states (state_name) VALUES ('ok');")
            self.__cur.execute("INSERT INTO states (state_name) VALUES ('deg');")
            self.__cur.execute("INSERT INTO states (state_name) VALUES ('nok');")
            self.__cur.execute("INSERT INTO states (state_name) VALUES ('fail');")
        else:
            self.__cur.execute("UPDATE g_nodes SET in_topo='f';")
            self.__cur.execute("UPDATE sg_edges SET in_topo='f';")
            self.__cur.execute("UPDATE g_edges SET in_topo='f';")
        self.commit()
    def ins(self,query):
        self.commit()
        self.__cur.execute(query)
        self.commit()
    def sel(self,query,debug=3):
        self.querys += 1
        self.commit()
        self.__cur.execute(query)
        self.commit()
        return self.__cur.fetchall()
    def selOne(self,query,debug=3):
        self.querys += 1
        self.commit()
        self.__cur.execute(query)
        self.commit()
        return self.__cur.fetchone()
    def getStatesName(self):
        query = "SELECT state_id,state_name FROM states"
        res = self.sel(query)
        acc = {}
        for row in res:
            (state_id,state_name) = row
            acc[state_name] = int(state_id)
        return acc
    def getStatesId(self):
        query = "SELECT state_id,state_name FROM states"
        res = self.sel(query)
        acc = {}
        for row in res:
            (state_id,state_name) = row
            acc[int(state_id)] = state_name
        return acc
    def evalStateId(self,id):
        return self.statesIds[int(id)]
    def evalStateName(self,name):
        return self.statesNames[name]
    def getSpines(self,root):
        # System (bei neueren Switches werden sie zu einem System zusammengefasst -> CAE2 GridDirector4200)
        query = "SELECT s_id,s_name,n_id,n_guid,n_name,nt_id,in_topo,nt_name FROM systems NATURAL JOIN nodes NATURAL JOIN nodetypes WHERE s_id='%s' AND nt_name in ('spine','root')" % (root.s_id)
        res = self.sel(query)
        
        # Chassis (die alten Switches von Voltaire werden durch das Chassis zusammengehalten, sysimgGUID ist nicht gleich)
        ## Chassis 1 (guid 0x8f104004050c6)
        ## sysimgguid=0x8f104004050c7              # Chassis 1
        ## sysimgguid=0x8f104004050bf              # Chassis 1
        query = "SELECT n_id,n_guid,n_name,s_id,nt_id,in_topo,nt_name FROM nodes NATURAL JOIN nodetypes WHERE s_id='%s' AND nt_name in ('spine','root')" % (root.s_id)
        return res
    def createSubgraph_ALT(self,name,type):
        query = "INSERT INTO subgraphs VALUES (NULL,'%s')" % name
        self.ins(query)
        query = "SELECT sg_id FROM subgraphs WHERE sg_name='%s'" % name
        res = self.sel(query)
        sg_id = res[0][0]
        #for k,options in self.cfg.get("topology").items():
        #    if type=="root": type="spine"
        #    r = "(%s)(.*)" % type
        #    m = re.match(r,k)
        #    if m:
        #        (t,pre) = m.groups()
        #        for k,v in options.items():
        #            if k=="none": continue
        #            option="%s [%s=%s]" % (pre,k,v)
        #            query = "INSERT INTO sg_options (sg_id,sgo) VALUES ('%s','%s')" % (sg_id,option)
        #            self.ins(query)
        option="graph [style=\"setlinewidth(0)\"]"
        query = "INSERT INTO sg_options (sg_id,sgo) VALUES ('%s','%s')" % (sg_id,option)
        self.ins(query)
        return sg_id
    def addNode(self,sg_id,node,shape=""):
        (n_id,name,nt_name) = node
        query = "SELECT * FROM g_nodes WHERE gn_name='%s' AND gn_shape='%s'" % \
                (name, shape)
        res = self.sel(query)
        if len(res) > 0:
            #print "Node '%s' schon in g_nodes vorhanden..." % name
            pass
        else:
            query = """INSERT INTO g_nodes (gn_id,sg_id,n_id,gn_name,gn_shape)
                        VALUES (NULL,'%s','%s','%s','%s')""" % \
                        (sg_id,n_id,name,shape)
            self.ins(query)
            if self.opt.debug >= 2:
                print query
            query = "UPDATE nodes SET in_topo='t' WHERE n_id='%s'" % n_id
            self.ins(query)
    def addCluster(self,sg_name):
        query = "INSERT INTO subgraphs (sg_name) VALUES ('%s')" % sg_name
        self.ins(query)
        query = "SELECT sg_id FROM subgraphs WHERE sg_name='%s'" % sg_name
        sg_id = self.selOne(query)[0]
        return sg_id
    def addSys(self,system,sg_id=0):
        (s_id,c_id,name,n_state_id, nt_name) = system
        query = "SELECT gn_id,sg_id,s_id,gn_name,gn_shape FROM g_nodes WHERE gn_name='%s'" % (name)
        res = self.sel(query)
        if len(res)>0:
            #print "Node '%s' schon in g_nodes vorhanden..." % name
            (gn_id,sg_id,s_id,gn_name,gn_shape) = res[0]
            return gn_id
        else:
            shape = ''
            # TODO: ugly hardcoded status
            if n_state_id==4: shape='box'
            query = "INSERT INTO g_nodes (gn_id,sg_id,s_id,gn_name,gn_shape) VALUES (NULL,'%s','%s','%s','%s')" % (sg_id, s_id, name,shape)
            self.ins(query)
            if self.opt.debug>=2 or name=="": print query
            query = "SELECT gn_id FROM g_nodes WHERE s_id='%s'" % s_id
            gn_id = self.selOne(query)
            query = "UPDATE nodes SET in_topo='t' WHERE s_id='%s'" % s_id
            self.ins(query)
            return gn_id
    def addChassis(self,system):
        query = "SELECT s_id FROM systems WHERE s_name='%s' AND c_id='%s'" % (system.c_name,system.c_id)
        res = self.sel(query)
        if len(res)==0:
            # Dazu sammeln wir die Daten der zu ersetzenden Knoten ein
            query = "select s_id,n_id from systems natural join nodes where c_id='%s'" % system.c_id
            res = self.sel(query)
            n_ids = [str(x[1]) for x in res]
            s_ids = [str(x[0]) for x in res]
            # Erstellen die Stelvs
            ## Erstelle Stelv-System 
            query = "INSERT INTO systems (s_name,c_id) VALUES ('%s','%s')" % (system.c_name, system.c_id)
            self.ins(query)
            query = "SELECT s_id FROM systems WHERE s_name='%s' AND c_id='%s'" % (system.c_name,system.c_id)
            res = self.selOne(query)
            s_id = res[0]
            system.s_rev = s_id
            ## Referenziere Altsysteme auf neues System
            query = "UPDATE systems SET s_rev='%s' WHERE s_id IN ('%s')" % (s_id,"','".join(s_ids))
            self.ins(query)

            ## Erstelle Stelv-Node
            ### nt_name='switch'
            query = "SELECT nt_id FROM nodetypes WHERE nt_name='switch'"
            res = self.selOne(query)
            nt_id = res[0]
            query = "INSERT INTO nodes (s_id,nt_id) VALUES ('%s','%s')" % (s_id,nt_id)
            self.ins(query)
            query = "SELECT n_id FROM nodes WHERE s_id='%s'" % s_id
            res = self.selOne(query)
            n_id = res[0]
            ## Referenziere Altnode auf neuen Node als n_rev
            query = "UPDATE nodes SET n_rev='%s' WHERE n_id IN ('%s')" % (n_id,"','".join(n_ids))
            self.ins(query)
        elif len(res)==1:
            #raise IOError("Chassis-System '%s' schon vorhanden..." % system.c_name)
            s_id = res[0]
        chassis_sys = uptopo.graphSys(system.c_name)
        chassis_sys.setOpts(s_id,'')
        chassis_sys.setNtName('switch')
        chassis_sys.setChassisId(system.c_id)
        return chassis_sys
    def getGnChilds(self,item):
        gn_id = item.gn_id
        query = "SELECT ge_dst_gnid, ge_dst FROM g_edges WHERE ge_src_gnid='%s'" % gn_id
        res = self.sel(query)
        gn_ids = []
        for row in res:
            (dst_gnid, dst_gn_name) = row
            gn_ids.append(dst_gnid)
        return gn_ids   
    def getSysChilds(self,s_id):
        res = self.getLinkList(s_id)
        systems = []
        for back in res:
            if back['s_s_id']==s_id:
                name =back['d_s_name']
                if name == 'None':
                    name = back['d_n_name']
                system = uptopo.graphSys(name)
                system.setOpts(back['d_s_id'], back['d_s_guid'])
                system.setLinkList(back)
                system.setNtName(back['d_nt_name'])
                systems.append(system)
            elif back['d_s_id']==s_id:
                name =back['s_s_name']
                if name == 'None':
                    name = back['s_n_name']
                system = uptopo.graphSys(name)
                system.setOpts(back['s_s_id'], back['s_s_guid'])
                system.setLinkList(back)
                system.setNtName(back['s_nt_name'])
                systems.append(system)
        return systems
    def getChilds(self,item):
        try:    n_id = item.n_id
        except: (s_id,s_name,n_id,n_guid,n_name,nt_id,in_topo,nt_name) = item
        query = "SELECT DISTINCT dlid FROM nodes NATURAL JOIN ports WHERE n_id='%s'" % n_id
        res = self.sel(query)
        n_ids = []
        for row in res:
            dlid = row
            queryC = "SELECT DISTINCT n_id FROM nodes NATURAL JOIN ports WHERE lid='%s' AND in_topo='f'" % dlid
            resC = self.sel(queryC)
            for rowC in resC:
                n_ids.append(rowC[0])
        return n_ids   
    def isEdgeSwitch(self,s_id):
        acc = True
        res = self.getLinkList(s_id)
        system = set([])
        for back in res:
            if back['s_nt_name']=='switch': system.add(back['s_n_name'])
            if back['d_nt_name']=='switch': system.add(back['d_n_name'])
        return len(system)<=2
    def getSystem(self,s_id):
        query = """SELECT   n1.n_id,
                            n1.n_name,
                            nt1.nt_name,
                            s1.s_name,
                            s1.s_guid,
                            s1.s_id,
                            c1.c_name,
                            s1.c_id
                        FROM nodes n1, nodetypes nt1,
                             systems s1, chassis c1
                        WHERE   n1.nt_id=nt1.nt_id AND
                                n1.s_id=s1.s_id AND
                                s1.c_id=c1.c_id AND
                                s1.s_id='%s'""" % (s_id)
        res = self.sel(query)
        for row in res:
            acc = {}
            (s_nid, s_nname, s_ntname, s_sname, \
             s_sguid, s_sid, s_cname,s_cid) = row
            acc['s_n_id']=s_nid
            acc['s_n_name']=s_nname
            acc['s_nt_name']=s_ntname
            acc['s_n_name']=s_sname
            acc['s_c_name']=s_cname
            acc['s_s_id']=s_sid
            acc['s_c_id']=s_cid
            acc['s_guid']=s_sguid
            return acc
        raise IOError("getSystem fuer s_id:'%s' hat kein Ergebnis!" % s_id)
    def getLinkList(self,s_id):
        query = """SELECT   l.l_id,
                            p1.p_lid,
                            p1.p_id,
                            p1.p_int,
                            n1.n_id,
                            n1.n_name,
                            n1.n_state_id,
                            nt1.nt_name,
                            s1.s_name,
                            s1.s_guid,
                            s1.s_id,
                            c1.c_name,
                            s1.c_id,
                            l.circle,
                            s2.c_id,
                            c2.c_name,
                            s2.s_id,
                            s2.s_guid,
                            s2.s_name,
                            nt2.nt_name,
                            n2.n_state_id,
                            n2.n_name,
                            n2.n_id,
                            p2.p_int,
                            p2.p_id,
                            p2.p_lid
                        FROM links l,ports p1,ports p2,nodes n1,nodes n2,
                             nodetypes nt1, nodetypes nt2, systems s1,
                             systems s2, chassis c1, chassis c2
                        WHERE   l.src   = p1.p_id AND
                                l.dst   = p2.p_id AND
                                p1.n_id = n1.n_id AND
                                p2.n_id = n2.n_id AND
                                n1.nt_id= nt1.nt_id AND
                                n2.nt_id= nt2.nt_id AND
                                n1.s_id = s1.s_id AND
                                n2.s_id = s2.s_id AND
                                s1.c_id = c1.c_id AND
                                s2.c_id = c2.c_id AND
                                (s1.s_id='%s' OR s2.s_id='%s')""" % (s_id,s_id)
        return self.getLinkListRes(query)
    def getLinkListGN(self,s_id):
        query = """SELECT   l.l_id,
                            p1.p_lid,
                            p1.p_id,
                            p1.p_int,
                            n1.n_id,
                            n1.n_name,
                            n1.n_state_id,
                            nt1.nt_name,
                            gn1.gn_id,
                            s1.s_name,
                            s1.s_guid,
                            s1.s_id,
                            c1.c_name,
                            s1.c_id,
                            l.circle,
                            s2.c_id,
                            c2.c_name,
                            s2.s_id,
                            s2.s_guid,
                            s2.s_name,
                            gn2.gn_id,
                            nt2.nt_name,
                            n2.n_state_id,
                            n2.n_name,
                            n2.n_id,
                            p2.p_int,
                            p2.p_id,
                            p2.p_lid
                        FROM links l,ports p1,ports p2,nodes n1,nodes n2,
                             nodetypes nt1, nodetypes nt2, systems s1,
                             systems s2,g_nodes gn1,g_nodes gn2,
                             chassis c1, chassis c2
                        WHERE   l.src = p1.p_id AND
                                l.dst=p2.p_id AND
                                p1.n_id=n1.n_id AND
                                p2.n_id=n2.n_id AND
                                n1.nt_id=nt1.nt_id AND
                                n2.nt_id=nt2.nt_id AND
                                n1.s_id=s1.s_id AND
                                n2.s_id=s2.s_id AND
                                s1.s_id=gn1.s_id AND
                                s2.s_id=gn2.s_id AND
                                s1.c_id=c1.c_id AND
                                s2.c_id=c2.c_id AND
                                (s1.s_id='%s' OR s2.s_id='%s')""" % (s_id,s_id)
        self.gnInside = True
        return self.getLinkListRes(query)
    def getLinkListAll(self):
        query = """SELECT   l.l_id,
                            p1.p_lid,
                            p1.p_id,
                            p1.p_int
                            n1.n_id,
                            n1.n_name,
                            n1.n_state_id,
                            nt1.nt_name,
                            gn1.gn_id,
                            s1.s_name,
                            s1.s_guid,
                            s1.s_id,
                            c1.c_name,
                            s1.c_id,
                            l.circle,
                            s2.c_id,
                            c2.c_name,
                            s2.s_id,
                            s2.s_guid,
                            s2.s_name,
                            gn2.gn_id,
                            nt2.nt_name,
                            n2.n_state_id,
                            n2.n_name,
                            n2.n_id,
                            p2.p_int,
                            p2.p_id,
                            p2.p_lid
                        FROM links l,ports p1,ports p2,nodes n1,nodes n2,
                             nodetypes nt1, nodetypes nt2, systems s1,
                             systems s2,g_nodes gn1,g_nodes gn2,
                             chassis c1, chassis c2
                        WHERE   l.src = p1.p_id AND
                                l.dst=p2.p_id AND
                                p1.n_id=n1.n_id AND
                                p2.n_id=n2.n_id AND
                                n1.nt_id=nt1.nt_id AND
                                n2.nt_id=nt2.nt_id AND
                                n1.s_id=s1.s_id AND
                                n2.s_id=s2.s_id AND
                                s1.s_id=gn1.s_id AND
                                s1.c_id=c1.c_id AND
                                s2.c_id=c2.c_id AND
                                s2.s_id=gn2.s_id"""
        return self.getLinkListRes(query)
    def getLinkListRes(self,query):
        res = self.sel(query)
        back = []
        for row in res:
            acc = {}
            if self.gnInside:
                (l_id, s_lid, s_p_id,s_port, s_nid, s_nname, s_n_state_id, \
                 s_ntname, s_gnid, s_sname, s_sguid, s_sid, s_cname,s_cid, \
                 circle, d_cid, d_cname,d_sid, d_sguid, d_sname, d_gnid, \
                 d_ntname, d_n_state_id, d_nname, d_nid, d_port, d_p_id, \
                 d_lid) = row
                acc['s_gn_id']=s_gnid
                acc['d_gn_id']=d_gnid
            else:
                (l_id, s_lid, s_p_id, s_port, s_nid, s_nname, s_n_state_id, s_ntname, \
                 s_sname, s_sguid, s_sid, s_cname,s_cid, circle, d_cid, \
                 d_cname,d_sid, d_sguid, d_sname, d_ntname, d_n_state_id, \
                 d_nname, d_nid, d_port, d_p_id, d_lid) = row
                
            acc['l_id']=l_id
            acc['s_p_lid']=s_lid
            acc['s_p_id']=s_p_id
            acc['s_p_int']=s_port
            acc['s_n_id']=s_nid
            acc['s_n_name']=s_nname
            acc['s_n_state_id']=s_n_state_id
            acc['s_nt_name']=s_ntname
            acc['s_s_name']=s_sname
            acc['s_c_name']=s_cname
            acc['s_s_id']=s_sid
            acc['s_c_id']=s_cid
            acc['s_s_guid']=s_sguid
            acc['circle']=circle
            acc['d_s_guid']=d_sguid
            acc['d_c_id']=d_cid
            acc['d_s_id']=d_sid
            acc['d_c_name']=d_cname
            acc['d_s_name']=d_sname
            acc['d_nt_name']=d_ntname
            acc['d_n_state_id']=d_n_state_id
            acc['d_n_name']=d_nname
            acc['d_n_id']=d_nid
            acc['d_p_int']=d_port
            acc['d_p_id']=d_p_id
            acc['d_p_lid']=d_lid
            back.append(acc)
        return back

    def addGEdges(self,item):
        (s_id,s_name,n_id,n_guid,n_name,nt_id,in_topo,nt_name) = item
        nids = self.getChilds(item)
        if n_name=='None' or n_name==None:
            name = s_name
        else:
            name = n_name
        for nid in nids:
            query = "SELECT s_name,n_name,nt_name FROM systems NATURAL JOIN nodes NATURAL JOIN nodetypes WHERE n_id='%s'" % nid
            res = self.selOne(query)
            (dst_sName,dst_nName,dst_type) = res
            if dst_nName=='None' or dst_nName==None:
                dst_name = dst_sName
            else:
                dst_name = dst_nName

            queryIns = "INSERT INTO g_edges VALUES (NULL,'%s','%s','%s','%s','f')" % (n_id,name,nid,dst_name)
            self.__cur.execute(queryIns)
            if dst_type in ('switch'):
                queryIns = "INSERT INTO g_switches (n_id,name) VALUES ('%s','%s')" % (nid,dst_name)
                try: self.__cur.execute(queryIns)
                except sqlite3.IntegrityError,e:
                    if True: pass
                    else:
                        self.deb(queryIns,2)
                        self.deb(e,2)
        self.commit()

    def addGSysEdge(self,src_sId,dst_sId):
        query = """SELECT gn_id,sg_id, gn_name FROM g_nodes JOIN systems
                    ON g_nodes.s_id=systems.s_id WHERE systems.s_id='%s'""" % \
                    src_sId
        res = self.selOne(query)
        try:
            (src_gnId, src_sgId, src_gnName) = res
        except:
            print query
            raise IOError
        query = """SELECT gn_id, sg_id, gn_name FROM g_nodes JOIN systems
                    ON g_nodes.s_id=systems.s_id WHERE systems.s_id='%s'""" % \
                    dst_sId
        res = self.selOne(query)
        try:
            (dst_gnId, dst_sgId, dst_gnName) = res
        except:
            print query
            raise IOError

        if src_sgId == dst_sgId != 0:
            query = """SELECT * FROM sg_edges
                            WHERE sge_src_gnid='%s' AND sge_dst_gnid='%s'
                            OR sge_src_gnid='%s' AND sge_dst_gnid='%s'""" % \
                            (src_gnId, dst_gnId, dst_gnId, src_gnId)
            res = self.sel(query)
            if len(res)!=0:
                return
            queryIns = """INSERT INTO sg_edges VALUES
                            (NULL,'%s', '%s','%s','%s','%s','f')""" % \
                        (src_sgId, src_gnId, src_gnName, dst_gnId, dst_gnName)
        else:
            query = """SELECT * FROM g_edges
                            WHERE ge_src_gnid='%s' AND ge_dst_gnid='%s'
                            OR ge_src_gnid='%s' AND ge_dst_gnid='%s'""" % \
                            (src_gnId, dst_gnId, dst_gnId, src_gnId)
            res = self.sel(query)
            if len(res)!=0:
                return
            queryIns = """INSERT INTO g_edges VALUES
                            (NULL,'%s','%s','%s','%s','f')""" % \
                            (src_gnId, src_gnName, dst_gnId, dst_gnName)
            print queryIns
        self.__cur.execute(queryIns)
        self.commit()

    def addSysSgNodesAndEdges(self,item,sg_id):
        (n_id,n_guid,name,s_id,nt_id,in_topo,nt_name) = (item.n_id,item.n_guid,item.name,item.s_id,item.nt_id,item.IamIn,item.nt_name)
        n_ids = self.getChilds(item)
        for dN_id in n_ids:
            query = "SELECT s_name,n_name,nt_name,in_topo,in_sg FROM systems NATURAL JOIN nodes NATURAL JOIN nodetypes WHERE n_id='%s'" % dN_id
            res = self.selOne(query)
            (dstS_name,dstN_name, dst_type,in_topo,in_sg) = res
            if dstN_name=='None':   dst_name = dstS_name
            else:                   dst_name = dstN_name
            if dst_type in ('switch','spine'):
                raise IOError('What\'s this for...')
                # Bei einem Switch legen wir eine g_edge an (Kante in keinem Subgraphen)
                queryIns = "INSERT INTO g_edges VALUES (NULL,'%s','%s','%s','%s','f')" % (n_id,name,dN_id,dst_name)
                self.__cur.execute(queryIns)
                if not in_sg=='t':
                    queryUp = "UPDATE nodes SET in_sg='t' WHERE n_id='%s'" % dN_id
                    self.__cur.execute(queryUp)
            else:
                queryIns = "INSERT INTO g_nodes (sg_id,n_id,gn_name ) VALUES ('%s','%s','%s')" % (sg_id,dN_id,dst_name)
                self.__cur.execute(queryIns)
                queryIns = "INSERT INTO sg_edges VALUES (NULL,'%s','%s','%s','%s','%s','f')" % (sg_id,n_id,name,dN_id,dst_name)
                self.__cur.execute(queryIns)
        self.commit()

    def addSgNodesAndEdges(self,item,sg_id):
        (n_id,n_guid,name,s_id,nt_id,in_topo,nt_name) = (item.n_id,item.n_guid,item.name,item.s_id,item.nt_id,item.IamIn,item.nt_name)
        n_ids = self.getChilds(item)
        for dN_id in n_ids:
            query = "SELECT s_name,n_name,nt_name,in_topo,in_sg FROM systems NATURAL JOIN nodes NATURAL JOIN nodetypes WHERE n_id='%s'" % dN_id
            res = self.selOne(query)
            (dstS_name,dstN_name, dst_type,in_topo,in_sg) = res
            if dstN_name == 'None':
                dst_name = dstS_name
            else:
                dst_name = dstN_name
            if dst_type in ('switch','spine'):
                # Bei einem Switch legen wir eine g_edge an (Kante in keinem Subgraphen)
                queryIns = "INSERT INTO g_edges VALUES (NULL,'%s','%s','%s','%s','f')" % (n_id,name,dN_id,dst_name)
                self.__cur.execute(queryIns)
                if not in_sg=='t':
                    queryUp = "UPDATE nodes SET in_sg='t' WHERE n_id='%s'" % dN_id
                    self.__cur.execute(queryUp)
                    queryIns = "INSERT INTO g_switches (n_id,name) VALUES ('%s','%s')" % (dN_id,dst_name)
                    self.__cur.execute(queryIns)
            else:
                queryIns = "INSERT INTO g_nodes (sg_id,n_id,gn_name ) VALUES ('%s','%s','%s')" % (sg_id,dN_id,dst_name)
                self.__cur.execute(queryIns)
                queryIns = "INSERT INTO sg_edges VALUES (NULL,'%s','%s','%s','%s','%s','f')" % (sg_id,n_id,name,dN_id,dst_name)
                self.__cur.execute(queryIns)
        self.commit()
    def getGSwitches(self):
        query = "SELECT n_id,name FROM g_switches"
        res = self.sel(query)
        query = "DELETE FROM g_switches"
        self.__cur.execute(query)
        return res
    def countChilds(self,item):
        query = "SELECT count(p_id) FROM systems NATURAL JOIN nodes NATURAL JOIN ports WHERE n_name='%s' AND uplink='f'" % item.n_name
        res = self.selOne(query)
        return res[0]
    def countSysChilds(self,item):
        query = "SELECT count(ge_id) FROM g_edges WHERE ge_src_gnid='%s'" % item.gn_id
        res = self.selOne(query)
        return res[0]
    def getSystems(self):
        query = """SELECT   DISTINCT s.s_id,s.c_id,s.s_guid,s.s_name,
                            (SELECT SUM(cir_cnt) FROM nodes WHERE s_id=s.s_id) AS cir_cnt,
                            (SELECT SUM(sw_cnt) FROM nodes WHERE s_id=s.s_id) AS sw_cnt,
                            (SELECT SUM(extSw_cnt) FROM nodes WHERE s_id=s.s_id) AS extSw_cnt,
                            (SELECT SUM(comp_cnt) FROM nodes WHERE s_id=s.s_id) AS comp_cnt
                        FROM systems s
                        WHERE s_rev='0'
                        ORDER BY cir_cnt, extSw_cnt DESC;"""
        systems = []
        res = self.sel(query)
        set_root = False
        for item in res:
            (s_id, c_id, s_guid, s_name, cir_cnt,
             sw_cnt, extSw_cnt, comp_cnt) = item
            if set_root:
                query = """UPDATE nodes SET nt_id=
                            (SELECT nt_id FROM nodetypes
                                    WHERE nt_name='root')"""
                if self.opt.ibsim:
                    # FIXME: A simple CLOS5 tricks my heuristic, because the spines
                    #       are connected to more switches (2xSwitch,1xCore) then
                    #       the core-Switch (only 2xSwitch) and there is _no_
                    #       Circle within the network :)
                    query += " WHERE n_name='core1'"
                else:
                    query += " WHERE s_id='%s'" % s_id
                self.ins(query)
                set_root = False
            query = "SELECT nt_name FROM nodes NATURAL JOIN nodetypes WHERE s_id='%s';" % s_id
            try: nt_name = self.selOne(query)[0]
            except:
                raise IOError(query)
            if s_name=='None':
                query = "SELECT n_name FROM nodes WHERE s_id='%s';" % s_id
                s_name = self.selOne(query)[0]
            system = uptopo.graphSys(s_name)
            system.setOpts(s_id,s_guid)
            system.setChassisId(c_id)
            system.setNtName(nt_name)
            system.setCnts(cir_cnt,sw_cnt,extSw_cnt,comp_cnt)
            res = self.getLinkList(s_id)
            for back in res:
                system.setLinkList(back)
                #def __init__(self,cDB, l_id, lid, sport, snid, circle, dnid, dport, dlid):
                edge = uptopo.graphEdge(self,back['l_id'], back['s_p_lid'], \
                                            back['s_p_id'],back['s_p_int'], \
                                            back['s_n_id'], back['circle'], \
                                            back['d_n_id'], back['d_p_int'], \
                                            back['d_p_id'], back['d_p_lid'])
                system.addEdge(edge)
            if len(res)==0:
                print "Keine Links fuer s_id '%s'" % s_id
            systems.append(system)
        return systems
    def isSwitch(self,gn_id,gn_name):
        # If there is no HCA within the node_desc its a switch
        return not re.search("HCA",gn_name)

    def sys2GNode(self, system, sg_id=0):
        """ Creates node within g_nodes and returns id """
        query = "SELECT gn_id FROM g_nodes WHERE s_id='%s'" % system.s_id
        res = self.selOne(query)
        if res != None:
            return res[0]
        else:
            query = "INSERT INTO g_nodes (sg_id,s_id,gn_name) VALUES"
            query += " ('%s','%s','%s')" % (sg_id, system.s_id, system.name)
            self.ins(query)
            query = "SELECT gn_id FROM g_nodes WHERE s_id='%s'" % system.s_id
            gn_id = self.selOne(query)[0]
            return gn_id

    def upsert_gno(self,key,val,gn_id):
        query = "SELECT gno_id, gno_val FROM gn_options WHERE gn_id='%s' AND gno_key='%s'" % (gn_id,key)
        res = self.selOne(query)
        if res!=None and res[1]!=val:
            query = "UPDATE gn_options SET gno_val='%s' WHERE gno_id='%s'" % (val,res[0])
            self.ins(query)
        elif key=='shape':
            query = "UPDATE g_nodes SET gn_shape='%s' WHERE gn_id='%s'" % (val,gn_id)
            self.ins(query)
        else:
            query = """INSERT INTO gn_options (gn_id,gno_key,gno_val)
                        VALUES ('%s', '%s', '%s')""" % (gn_id,key,val)
            self.ins(query)
    def getLinkPerf(self, src_name, dst_name):
        # Get p_ids
        query = """SELECT p1.p_id, l.width, l.speed
                FROM links l, ports p1, nodes n1, ports p2, nodes n2
                WHERE l.src=p1.p_id AND p1.n_id=n1.n_id AND n1.n_name='%s'
                AND l.dst=p2.p_id AND p2.n_id=n2.n_id AND n2.n_name='%s'""" % \
                (src_name,dst_name)
        res = self.sel(query)
        if len(res)!=1:
            # FIXME: Multiple connections between nodes?!
            pass
        for row in res:
            (src_pid, width, speed) = row
        # xmit_traffic
        query = """SELECT pk_id, pk_name, pc_val FROM perfcache
                        NATURAL JOIN perfkeys WHERE p_id='%s'""" % src_pid
        res = self.sel(query)
        acc = {'max_data':int(int(speed)*int(width)), 'width':width, 'speed':speed}
        for row in res:
            (pk_id, pk_name, pc_val) = row
            acc[pk_name] = pc_val
        return acc

class topology(object):
    def __init__(self,rDB,cDB,opt,cfg,log):
        self.log = log
        self.cDB = cDB
        self.rDB = rDB
        self.opt = opt
        self.cfg = cfg

    def deb(self, msg, deb):
        if self.opt.dot and self.opt.debug >= deb:
            print msg

    def eval(self):
        self.log.start()
        cDB = self.cDB
        self.root = nodeNid(self.opt, cDB, self.cfg, None)
        # root ist bestimmt, nun schauen wir ob es gleichartige spines gibt in dem Chassis / System
        self.recursiv(self.root)
        self.log.end("evalTopo")

    def drawChassis(self, fd):
        c_query = "SELECT c_id,c_name FROM chassis"
        c_res = self.cDB.sel(c_query)
        for c_row in c_res:
            (c_id, c_name) = c_row
            # Erstelle sg_node der Chassis representiert
            gn_id = self.cDB.addChassis(c_id, c_name)
            # Male diesen Knoten, alle Kanten muessen dann auf diesen Knoten umgebogen werden...
            self.drawNode(fd, gn_id)

    def write(self, fd, line):
        fd.write("%s%s\n" % ("\t" * self. tab, line))

    def fixPositions(self):
        self.log.start("fixPos")
        if self.opt.graphviz_cmd != "":
            cmd = "%s -Tdot %s" % (self.opt.graphviz_cmd, self.rFb)
        (ec, out) = commands.getstatusoutput(cmd)
        if ec != 0:
            print out
            sys.exit(2)
        if 1:
            fd = open("/tmp/out.dot", "w")
            fd.write(out)
            lines = out.split("\n")
        else:
            fd = open("/tmp/out.dot", "r")
            lines = fd.readlines()
        fd.close()
        # Defaults
        self.sg_id = 0
        self.typ = None
        self.subgraph = None
        for line in lines:
            self.matchGraph(line)
            self.matchNode(line)
            self.matchEdge(line)
        self.log.end("fixPos")

    def matchEdge(self, line):
        """ We don't need this function anymore, because while create the topo
        we assume that we don't get eyecandy-options. Maybe we should reconsider
        this to implement different edge sizes """
        return
        #s1c1 -> l1c1 [pos="712.01,738.06 677.54,649.48 550.75,323.71 519.36,243.03"];
        reg = '[ \t]+([a-zA-Z0-9]+) -> ([a-zA-Z0-9]+)[ \t]+\[(.+)\];'
        mat = re.search(r, line)
        if mat:
            (src, dst) = (mat.group(1), mat.group(2))
            opts = mat.groups()[2:]
    def matchNode(self,line):
        r ='^[ \t]*([a-zA-Z0-9]+)[ \t]+\[(.+)\];'
        m = re.match(r,line)
        if m:
            node = m.group(1)
            opts = m.groups()[1:]
            if node not in ('node','edge','graph'):
                 self.alterNode(node,opts[0])
    def matchGraph(self,line):
        # Befinden wir uns in einem subgraph?
        r = "(diagraph|subgraph)[ \t]+([\_a-zA-Z0-9]+)"
        m = re.search(r,line)
        if m:
            (gtyp,gname) = m.groups()
            if gtyp=="diagraph": self.sg_id = 0
            else:
                self.subgraph = gname.split("_")[1]
                query = "SELECT sg_id FROM subgraphs WHERE sg_name='%s'" % self.subgraph
                res = self.cDB.selOne(query)
                self.sg_id = res[0]
                self.log.debug("##### Subgraph '%s' mit id '%s' startet" % (self.subgraph,self.sg_id),1)
        if line=="\t}":
            self.log.debug("Subgraph '%s' mit id '%s' endet" % (self.subgraph,self.sg_id),1)
            self.subgraph = ""
            self.sg_id = 0
        # Matche graph-Options
        if self.typ!=None:
            #print "%s %s ff" % ("#"*1,self.typ)
            r = '([a-z]+)=(\"[a-z0-9\,\.]+\")'
            m = re.search(r, line)
            if m:
                self.alterSubgraphOptions(self.sg_id, m.groups())
            r = '([a-z]+)=([a-z0-9\.]+)'
            m = re.search(r, line)
            if m:
                self.alterSubgraphOptions(self.sg_id, m.groups())
            if re.search("\];",line):
                self.typ = None
        r = "[ \t]+(graph|node|edge)[ \t]+"
        m = re.search(r,line)
        if m:
            self.typ = m.group(1)
            r = '([a-z]+)=(\"[a-z0-9\,\.]+\")'
            m = re.search(r, line)
            if m:
                self.alterSubgraphOptions(self.sg_id, m.groups())
            r = '([a-z]+)=([a-z0-9\.]+)'
            m = re.search(r, line)
            if m:
                self.alterSubgraphOptions(self.sg_id, m.groups())
            ## Wenn der type vorbei ist, muss man ein "];" gesehen haben
            r = "\];$"
            if re.search(r,line):
                self.typ = None
    def alterSubgraphOptions(self,sg_id,opts):
        query = "INSERT INTO sg_options VALUES (NULL,'%s','%s [%s=%s]')" % (sg_id,self.typ,opts[0],opts[1])
        try: self.cDB.ins(query)
        except sqlite3.IntegrityError, e: pass
    def alterNode(self,node,opts):
        query = "SELECT gn_id FROM g_nodes WHERE gn_name='%s'" % node
        res = self.cDB.selOne(query)
        if len(res)!=1:
            raise IOError("Node '%s' nicht vorhanden" % node)
        gn_id = res[0]
        for opt in opts.split(", "):
            opt_dingens = opt.split("=")
            if len(opt_dingens)==2:
                (k,v) = opt_dingens
            elif len(opt_dingens)>=3:
                (k, v) = (opt_dingens[0], "=".join(tuple(opt_dingens[1:])))
            self.cDB.upsert_gno(k, v, gn_id)


class myTopo(topology):
    """ Ueberladen der eigentlichen topology-Klasse """
    def create(self, graph=None):
        """ If no graph is given we just draw a plain graph without eye candy """
        self.graph = graph
        # port vor locality, da evallink dort durchgefuehrt wird
        self.log.start("create")
        cDB = self.cDB
        self.rFb = "/tmp/%s.dot" % "".join(random.sample('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 10))
        if self.opt.debug >= 1:
            print self.rFb
        fd = open(self.rFb, "w")
        self.tab = 0
        self.write(fd, "digraph G { overlap=none;")
        # Set edges and nodes to be in the topology
        query = "UPDATE g_nodes SET in_topo='f'"
        res = cDB.ins(query)
        query = "UPDATE sg_edges SET in_topo='f'"
        res = cDB.ins(query)
        query = "UPDATE g_edges SET in_topo='f'"
        res = cDB.ins(query)

        # Graph-Options
        query = "SELECT sgo FROM sg_options WHERE sg_id='0'"
        res = cDB.sel(query)
        self.tab += 1
        #self.drawChassis(fd) 
        for row in res:
            self.write(fd, "%s;" % row)
        query = "SELECT * FROM subgraphs WHERE sg_name!='empty'"
        res = cDB.sel(query)
        # hmm
        for row in res:
            self.drawSubgraph(fd, row)
        # spine-Links schreiben
        self.drawGNodes(fd)
        self.drawGEdges(fd)

        self.write(fd, "}")
        fd.close()
        #self.svg()
        self.log.end("create")
        self.log.finish("create")

    def svg(self):
        cmd = "neato -n1 -Tsvg -o/srv/www/qnib/root_%s.svg %s" % (self.graph, self.rFb)
        #cmd = "neato -n1 -Tsvg -o/tmp/root_%s.svg %s" % (self.graph,self.rFb)
        if self.opt.debug >= 1:
            print cmd
        (ec, out) = commands.getstatusoutput(cmd)
        if ec != 0:
            print out
            raise IOError

    def drawSgNodes(self, fd, sg_id):
        query = """SELECT sg_id, gn.c_id, gn.s_id, gn.n_id,
                    (SELECT state_name FROM states WHERE state_id=n_state_id)
                    AS n_status,
                    gn_id,gn_name,gn_shape
                FROM g_nodes gn JOIN nodes n ON n.s_id=gn.s_id
                WHERE sg_id='%s' AND gn.in_topo='f'""" % sg_id
        res = self.cDB.sel(query)
        for row in res:
            opts = ""
            (sg_id, c_id, s_id, n_id, n_status, \
             gn_id, gn_name, gn_shape) = row
            item = nodeGnId(self.opt, self.cDB, self.rDB, self.cfg, gn_id)
            item.setNodeInfo(row, self.graph)
            if self.graph != None:
                opts = item.getNodeOpts()
            self.write(fd, "\"%s\" %s;" % (gn_name, opts))
            item.setInTopo()

    def drawGNodes(self, fd):
        query = """SELECT sg_id, gn.c_id, gn.s_id, gn.n_id,
                    (SELECT state_name FROM states WHERE state_id=n_state_id)
                    AS n_status,
                    gn_id,gn_name,gn_shape
                FROM g_nodes gn JOIN nodes n ON n.s_id=gn.s_id
                WHERE gn.in_topo='f'"""
        res = self.cDB.sel(query)
        for row in res:
            opts = ""
            (sg_id, c_id, s_id, n_id, n_status, \
             gn_id, gn_name, gn_shape) = row
            item = nodeGnId(self.opt, self.cDB, self.rDB, self.cfg, gn_id)
            item.setNodeInfo(row, self.graph)
            if self.graph != None:
                opts = item.getNodeOpts()
            self.write(fd, "\"%s\" %s;" % (gn_name, opts))
            item.setInTopo()

    def drawNode(self, fd, gn_id):
        query = """SELECT sg_id,c_id,n.s_id,n.n_id,
                    (SELECT state_name FROM states WHERE state_id=n.n_state_id)
                    AS n_status,
                    gn_id,gn_name,gn_shape
                FROM g_nodes gn JOIN nodes n ON gn.s_id=n.s_id
                WHERE gn_id='%s'""" % gn_id
        res = self.cDB.sel(query)
        for row in res:
            opts = ""
            (sg_id, c_id, s_id, n_id, n_status, \
             gn_id, gn_name, gn_shape) = row
            item = nodeGnId(self.opt, self.cDB, self.rDB, self.cfg, gn_id)
            item.setNodeInfo(row, self.graph)
            if self.graph != None:
                opts = item.getNodeOpts()
            self.write(fd, "\"%s\" %s;" % (gn_name,opts))
            item.setInTopo()

    def drawGEdges(self, fd):
        query = "SELECT ge_src_gnid, ge_src, ge_dst_gnid, ge_dst "
        query += "FROM g_edges WHERE in_topo='f'"
        res = self.cDB.sel(query)
        rowS = set([])
        # ugly hack to prevent multiple links being drawn multiple times
        for row in res:
            rowS.add(row)
        for row in rowS:
            edge = edgeClass(self.opt, self.cDB, self.cfg, self.log)
            edge.setInfo(row, self.graph)
            # edge.evalLinks()
            self.write(fd, edge.getEdgeStr(self.graph))
            edge.setInTopo()

    def drawSgEdges(self, fd, sg_id):
        sg_query = "SELECT gn_id, gn_name FROM g_nodes WHERE sg_id='%s'" % sg_id
        sg_res = self.cDB.sel(sg_query)
        for sg_row in sg_res:
            (gn_id, gn_name) = sg_row
            query = "SELECT sge_src_gnid, sge_src, "
            query += "sge_dst_gnid, sge_dst "
            query += "FROM sg_edges WHERE sge_src_gnid='%s' " % gn_id
            query += "AND in_topo='f'"
            res = self.cDB.sel(query)
            rowS = set([])
            # ugly hack to prevent multiple links being drawn multiple times
            for row in res:
                rowS.add(row)
            for row in rowS:
                (sge_src_gnid, sge_src, sge_dst_gnid, sge_dst) = row
                edge = edgeClass(self.opt, self.cDB, self.cfg, self.log)
                edge.setInfo(row, self.graph)
                edge.setInTopo()
                # Die Links muessen nur evaluiert werden, wenn der port-Graph erstellt wird
                #if self.graph in ('port','locality','congestion'): edge.evalLinks()
                self.write(fd, edge.getEdgeStr(self.graph))
                self.drawNode(fd, sge_dst_gnid)

    def drawSubgraph(self, fd, sg):
        (sg_id, sg_name) = sg
        # Start
        self.write(fd, "subgraph cluster_%s {" % sg_name)
        self.tab += 1
        # Options reinfuschen
        option = "graph [style=\"setlinewidth(0)\"];"
        self.write(fd, option)
        # options
        query = "SELECT sgo_id,sg_id,sgo FROM sg_options WHERE sg_id='%s'" % sg_id
        res = self.cDB.sel(query)
        for row in res:
            (sgo_id, sg_id, sgo) = row
            self.write(fd, "%s;" % sgo)
        #nodes
        self.drawSgNodes(fd, sg_id)
        # links
        self.drawSgEdges(fd, sg_id)
        # end
        self.write(fd, "}")
        self.tab -= 1

    def extraEdgeOptsPort(self, item):
        pass


class Parameter(object):
    def __init__(self, argv):
        # Parameterhandling
        usageStr = "<bin> [options]"
        self.parser = OptionParser(usage=usageStr)
        self.default()

        (self.options, args) = self.parser.parse_args()

        # copy over all class.attributes
        self.__dict__ = self.options.__dict__
        self.args = args

    def default(self):
        # Default-Options
        self.parser.add_option("-d", dest="debug", action="count",
            help="increases debug [default:None, -d:1, -ddd: 3]")
        self.parser.add_option("-C", dest="netcfg",
            default="/root/QNIB/serverfiles/usr/local/nagios/etc/netgraph.cfg",
            action="store", help="Network configfile (default: %default)")
        self.parser.add_option("-t", dest="topocfg",
            default="/root/QNIB/serverfiles/usr/local/nagios/etc/topology.cfg",
            action="store", help="Topology configfile (default: %default)")
        self.parser.add_option("-c", dest="cfgfile",
            default="/root/QNIB/serverfiles/usr/local/etc/default.cfg",
            action="store", help="Configfile (default: %default)")
        self.parser.add_option("-g", dest="graph", default="plain",
            action="store", help="Graph to create (default: %default)")
        self.parser.add_option("--parse", dest="parse", default=False,
            action="store_true", help="Show parsing debug information")
        self.parser.add_option("--circle", dest="circle", default=False,
            action="store_true", help="Show circle debug information")
        self.parser.add_option("--links", dest="links", default=False,
            action="store_true", help="Show link analysis debug information")
        self.parser.add_option("--db", dest="db", default=False,
            action="store_true", help="Show database debug information")
        self.parser.add_option("--dot", dest="dot", default=False,
            action="store_true", help="Show graphviz debug information")
        self.parser.add_option("--loop", dest="loop", default=False,
            action="store_true", help="Loop the script")
        self.parser.add_option("--graphviz-cmd", dest="graphviz_cmd",
            default="twopi", action="store",
            help="Graphviz cmd to layout graph (default: %default)")
        self.parser.add_option("--delay", dest="loop_delay", default=11,
            action="store",
            help="Delay in seconds if loop is set (default: %default)")
    def check(self):
        pass


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
