#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Bibliotheken laden
import re, os, sys, commands
from optparse import OptionParser
import pgdb, datetime
import time

sys.path.append('/root/QNIB/serverfiles/usr/local/lib/')
import dbCon
import libTopology

class Parameter(object):
    def __init__(self):
        # Parameterhandling
        usageStr = "parse_ibnetdiscover [options]"
        self.parser = OptionParser(usage=usageStr)
        self.default()
        self.extra()
        (self.options, args) = self.parser.parse_args()

        # copy over all class.attributes
        self.__dict__ = self.options.__dict__
        self.args = args
    def default(self):
        # Default-Options
        self.parser.add_option("-d", action="count", dest="debug", help="increases debug [default:None, -d:1, -ddd: 3]")
        self.parser.add_option("-f", dest="file", default="", action="store", help="file which contains the ibnetdiscover-output")
        self.parser.add_option("-L", dest="lids", default=False, action="store", help="lid to debug (all other debug information will be supressed)")
        self.parser.add_option("--check-traps", dest="check_traps", default=False, action="store_true", help="check for traps stored in the DB inserted from opensm")
        self.parser.add_option("-c", dest="cfgfile", default="/root/QNIB/serverfiles/usr/local/etc/default.cfg", action = "store", help = "Configfile (default: %default)")
        self.parser.add_option("--loop", dest="loop", default=False, action = "store_true", help = "Loop the script")
        self.parser.add_option("--delay", dest="loop_delay", default=10, action = "store", help = "Delay in seconds if loop is set (default: %default)")
        self.parser.add_option("--parse", dest="parse", default=False, action = "store_true", help = "Show parsing debug information")
        self.parser.add_option("--circle",dest="circle",default=False, action = "store_true", help = "Show circle debug information")
        self.parser.add_option("--links",dest="links",default=False, action = "store_true", help = "Show link analysis debug information")
        self.parser.add_option("--db",dest="db",default=False, action = "store_true", help = "Show database debug information")
        self.parser.add_option("--force-uptopo",dest="force_uptopo",default=False, action = "store_true", help = "Force update of topology")
    def extra(self):
        pass 
    def check(self):
        if self.debug==None: self.debug = 0
        if self.lids:
            lids = self.lids.split(",")
            self.lids = set(lids)
        self.nodeGuids = {}

def hasItems(l1,l2):
    #print l1,l2
    for l in l1:
        check = l in l2
        if check: return True
    return False

class swPort(object):
    def __init__(self,opt,switch,line, match):
        self.line       = line
        self.opt        = opt
        self.switch     = switch
        self.match      = match
        self.dportguid = ''
        self.ext_port   = False
        self.dext_port   = False
    def deb(self,lids,msg,deb=0):
        if self.opt.lids and hasItems(lids,self.opt.lids):
            print msg
        elif self.opt.debug>=deb:
            print msg
    def matching(self):
        (self.port,self.type,self.dguid,self.dport,self.dportguid,self.dname,self.dlid,self.width,self.speed) = self.match.groups()
    def eval(self,db,cfg):
        self.matching()
        # Meine Switchports zuerst
        switch = self.switch
        src = switch.createPort(self.port,'',switch.lid)
    
        pm = re.search("([a-z0-9]+)",self.dportguid,re.I)
        # TODO: Muss ich hier unterscheiden? Hoffe nicht.... :)
        if pm:
            self.dportguid = pm.group(1)
        else:
            self.dportguid = ''
        s_lids = switch.getLids()
        s_lids.add(self.dlid)
        self.deb(s_lids,"Matche Switch-Port: p:%s dguid:%s dp:%s dpguid:%s dn:%s dl:%s w:%s s:%s" % (self.port,self.dguid,self.dport,self.dportguid,self.dname,self.dlid,self.width,self.speed),1)
        node = self.opt.nodeGuids[self.dguid]
        dst = node.createPort(self.dport,self.dportguid,self.dlid)
        self.deb(s_lids,"### %s" % node.__str__(),1)
        linkCandidate = libTopology.parseLink(db,self.opt,cfg)
        l_id = db.insLink(src,dst,self.width,self.speed)
        linkCandidate.setLinkID(l_id)
        node.updateDB()
        # Link-Kandidate
        # setOpts gibt den Kandidaten zurück, wenn er nicht existiert, existenten link sonst
        link          = linkCandidate.setOpts(self.switch,self.port,node,self.dport)
        self.deb(self.switch.getLids(),"An Switch %s> %s" % (self.switch.__str__(),link),2)

class swPortExt(swPort):
    def matching(self):
        (self.port,self.ext_port,self.type,self.dguid,self.dport,self.dportguid,self.dname,self.dlid,self.width,self.speed) = self.match.groups()
class swPortDExt(swPort):
    """ SourcePort is not modular - DstPort is """
    def matching(self):
        (self.port,self.type,self.dguid,self.dport,self.dext_port,self.dname,self.dlid,self.width,self.speed) = self.match.groups()
class swPortExtExt(swPort):
    def matching(self):
        (self.port,self.ext_port,self.type,self.dguid,self.dport,self.dext_port,self.dname,self.dlid,self.width,self.speed) = self.match.groups()

class checks(object):
    def __init__(self, db, options, cfg, log):
        self.db = db
        self.cfg = cfg
        self.opt = options
        self.log = log
        self.log.start("create")
        self.log_file = "/var/log/parse_ibnetdiscover.log"
        self.retEC = 0
        self.start = int(datetime.datetime.now().strftime("%s"))
        self.stateIds = self.db.getStatesId()
        self.stateNames = self.db.getStatesName()
        query = "UPDATE ports SET p_state_id='%s'" % (self.stateNames['chk'])
        db.exe(query)
        self.statusList = []
        self.perfList = []
        self.hostPat = "" #cfg.get('hostpat')
        self.chassisNames = cfg.get('chassis')
        self.sysGuids = {}
        self.swPorts  = []
        self.cNr = None
    def evalSwPorts(self,cfg):
        for swP in self.swPorts:
            swP.eval(self.db,cfg)
    def ibnetdiscover(self):
        db          = self.db
        self.chassis     = {}
        
        if self.opt.file=="":
            cmd = "sudo  LD_PRELOAD=/usr/local/lib/umad2sim/libumad2sim.so /usr/local/sbin/ibnetdiscover -g"
            (ec,out) = commands.getstatusoutput(cmd)
            if ec!=0:
                self.statusList = [out+"ibnetdiscover failed"]
                self.retEC = 2
            lines = out.split("\n")
        else:
            ibfile = "/root/kniepch/IB_FlowAndCongestionControl/serverfiles/%s" % self.opt.file
            fd = open(ibfile,"r")
            lines = fd.readlines()
            fd.close()
        bool = False
        self.sysimgguid = None
        cId = None
        # Wir muessen erstmal alle Systems und Nodes sichten, bevor wir uns an die Links machen
        for line in lines:
            if self.matchContinue(line):
                continue
            
            ################################
            ## Spezielle Matches
            # hostports enthalten noch ihre portguid und srclid
            # [1](8f1040399094d)      "S-0008f104004127bc"[6]         # lid 9 lmc 0 "ISR9024S-M Voltaire" lid 1 4xSDR
            r = "\[(\d+)\]\(([a-f0-9]+)\).*\"S-[0]*[a-f0-9]+\"\[(\d+)\].*lid (\d+) lmc.*lid (\d+) (\d+)x([A-Z]DR).*"
            m = re.match(r,line)
            if m and self.sysimgguid:
                    # Port gefunden
                    (port,guid,dport,slid,dlid,width,speed) = m.groups()
                    self.deb(set([slid,dlid]),"Matche %s-Hostport: " % (self.sysimgguid,line),"p",3)
                    db.updatePort(nId,port,dport,slid,dlid,width,speed)
                    bool = False
                    continue
            
            # Ich bin ein Chassismodul, da gibt es noch sowas wie [ext X]
            # [15][ext 15]    "S-0008f105002013b2"[32]                # "Voltaire 4036 # sw36" lid 419 4xDDR
            r = "^\[(\d+)\]\[ext (\d+)\].*\"[SH]-[0]*([a-z0-9]+)\"\[(\d+)\].*lid[ \t](\d+) (\d+)x([SDQ]DR)"
            m = re.match(r,line)
            if m and self.sysimgguid and cId:
                    # Port gefunden
                    (port,extport,guid,dport,dlid,width,speed) = m.groups()
                    self.deb(set([dlid]),"Matche %s-Chassisport %s: " % (cId,port),"p",1)
                    db.updateChassisPort(nId,port,dport,slid,dlid,width,speed,extport)
                    continue
            # Chassismodul mit Knoten an anderer Seite
            # [14][ext 2]     "H-003048c1b2300000"[1](3048c1b2300001)                 # "harper132 HCA-1" lid 865 4xDDR
            
            # Reset von allen Board-Spezifika
            r = "^vendid.*"
            m = re.match(r,line)
            if m:
                chip        = None
                lb          = None
                fb          = None
                chassisNr   = None
                
            
            
            if self.matchChassis(line): continue
            # sysimgguid (mit/ohne Chassis)
            if self.matchSystem(line): continue
            # Modulare Switches
            if self.matchSwitch(line): continue
            # CA
            if self.matchCA(line): continue
        for line in lines:
            if self.matchContinue(line):
                continue
            # Modulare Switches
            if self.matchSwitch(line,True): continue
            # switchport
            if self.matchSwitchPortGen(line): continue
            
        end = int(datetime.datetime.now().strftime("%s"))
        self.wall = end - self.start
        self.statusList.append("%s querys" % db.querys)
        self.statusList.append("%s commits" % db.commits)
        self.perfList.append("querys=%s" % db.querys)
        self.perfList.append("commits=%s" % db.commits)
    def matchChassis(self,line):
        # chassis
        ## Chassis 1 (guid 0x8f104004050c6)
        r = "Chassis (\d+) \(guid 0x([0-9a-f]+)\)"
        m = re.match(r,line)
        if m:
            self.cNr                = m.group(1)
            chassisguid             = m.group(2)
            self.chassis[self.cNr]  = chassisguid
            cId = self.db.getIns_ID('chassis',"c_guid='%s'" % str(chassisguid),['c_guid','c_nr','c_name'], \
                                    [str(chassisguid),self.cNr,self.chassisNames[chassisguid]['name']])
        return m
    def matchContinue(self,line):
        # HCA-Zeilen
        # [1](guid)
        r='^\[1\]\(.*'
        #if re.match(r,line): continue
        
        # Leerzeilen
        r='^[ \t]+$'
        if re.match(r,line): return True
        
        # vendid/devid/caguid
        r='^(vend|dev|cagu)id.*'
        if re.match(r,line): return True
        
        # Auskommentiertes
        r='^#.*'
        if re.match(r,line): return True
        return False
    def matchSwitchPortGen(self,line,guid=False):
        if guid and re.search(guid,line): print line
        acc = self.matchSwitchPortExtExt(line, guid)
        if acc: return True
        acc = self.matchSwitchPortDExt(line, guid)
        if acc: return True
        acc = self.matchSwitchPortExt(line, guid)
        if acc: return True
        acc = self.matchSwitchPort(line, guid)
        if acc: return True
        return False
    def matchSwitchPort(self,line,guid):
        r = "^\[(\d+)\][ \t]+\"([SH])-[0]*([a-z0-9]+)\"\[(\d+)\](.*)#[ \t]+\"(.*)\"[ \t]+lid[ \t](\d+) (\d+)x([A-Z]DR)"
        m = re.match(r,line)
        if m:
            if guid and re.search(guid,line): print "Sw -> got it"
            # Port gefunden
            #(self.port,self.type,self.dguid,self.dport,self.dportguid,self.dname,self.dlid,self.width,self.speed) = self.match.groups()
            self.swPorts.append(swPort(self.opt,self.switch,line,m))
            return True
        return False
    def matchSwitchPortExt(self,line,guid):
        r = "^\[(\d+)\]\[ext (\d+)\][ \t]+\"([SH])-[0]*([a-z0-9]+)\"\[(\d+)\](.*)#[ \t]+\"(.*)\"[ \t]+lid[ \t](\d+) (\d+)x([A-Z]DR)"
        m = re.match(r,line)
        if m:
            if guid and re.search(guid,line): print "SwExt -> got it"
            # Port gefunden
            self.swPorts.append(swPortExt(self.opt,self.switch,line,m))
            return True
        return False
    def matchSwitchPortDExt(self,line,guid):
        #Sw [1]  "S-0008f104003f63de"[14][ext 14]
        r = "^\[(\d+)\][ \t]+\"([SH])-[0]*([a-z0-9]+)\"\[(\d+)\]\[ext (\d+)\].*#[ \t]+\"(.*)\"[ \t]+lid[ \t](\d+) (\d+)x([A-Z]DR)"
        m = re.match(r,line)
        if m:
            if guid and re.search(guid,line): print "SwDExt -> got it"
            # Port gefunden
            #(self.port,self.type,self.dguid,self.dport,self.dportguid,self.dname,self.dlid,self.width,self.speed) = self.match.groups()
            self.swPorts.append(swPortDExt(self.opt,self.switch,line,m))
            return True
        return False
    def matchSwitchPortExtExt(self,line, guid):
        #[14][ext 2]	"S-0008f104003f5c40"[24][ext 15]		# "ISR9288/ISR9096 Voltaire sLB-24" lid 208 4xSDR
        #[15][ext 15]    "S-0008f104003f5c43"[22][ext 19]                # "ISR9288/ISR9096 Voltaire sLB-24" lid 211 4xSDR
        r = "^\[(\d+)\]\[ext (\d+)\][ \t]+\"([SH])-[0]*([a-z0-9]+)\"\[(\d+)\]\[ext (\d+)\].*#[ \t]+\"(.*)\"[ \t]+lid[ \t](\d+) (\d+)x([A-Z]DR)"
        m = re.match(r,line)
        if m:
            if guid and re.search(guid,line): print 'SwExtExt -> got it'
            # Port gefunden
            self.swPorts.append(swPortExtExt(self.opt,self.switch,line,m))
            return True
        return False
    def matchCA(self,line):
        # systemguid eines Chassis
        r = '.*H-[0]*([a-z0-9]+).*# "(.*)".*'
        m = re.match(r,line)
        if m:   
            (guid,name) = m.groups()
            if self.opt.nodeGuids.has_key(guid):
                node = self.opt.nodeGuids[guid]
            else:
                node = libTopology.parseNode(self.db,self.opt,self.cfg,self.opt.nodeGuids)
            node.setHost()
            node.setSys(self.sys)
            node.setName(name)
            node.setGuid(guid)
            node.updateDB()
            self.node = node
            return True
        return False
    def matchSystem(self,line):
        # systemguid eines Chassis
        r = "sysimgguid=0x([0-9a-f]+)[ \t]+# Chassis (\d+)"
        m = re.match(r,line)
        if m:   
                self.sys = libTopology.parseSystem(self.db,self.opt,self.cfg,self.sysGuids)
                self.sys.setGuid(m.group(1))
                self.sys.evalGuid()
                self.sys.setChassisNr(self.cNr)
                return True
        # systemguid
        r = "sysimgguid=0x([0-9a-f]+)"
        m = re.match(r,line)
        if m:
                self.cNr = None
                self.sys = libTopology.parseSystem(self.db,self.opt,self.cfg,self.sysGuids)
                self.sys.setGuid(m.group(1))
                self.sys.evalGuid()
                return True
        return False
    def matchSwitch(self,line,light=False):
        db = self.db
        # Switch  36 "S-0008f1050065097c"         # "Voltaire sLB-4018    Line 9  Chip 1 4200 #4200-C8F8" enhanced port 0 lid 7 lmc 0
        r = '.*S-[0]*([a-z0-9]+).*# "(.*)".*lid (\d+) lmc'
        m = re.match(r,line) 
        if  m:
            (guid,name,lid) = m.groups()
            if self.opt.nodeGuids.has_key(guid):
                self.deb(set([lid,]),"Switch '%s (guid:%s / lid:%s)' schon drin?" % (name,guid,lid),'p',0)
                switch = self.opt.nodeGuids[guid]
            else:
                switch = libTopology.parseNode(self.db,self.opt,self.cfg,self.opt.nodeGuids)
                switch.setSys(self.sys)
                switch.setSwitch()
                switch.setLid(lid)
                switch.setGuid(guid)
                switch.setName(name)
                self.deb(switch.getLids(),"## Switch: %s" % switch,"p",1)
                switch.updateDB()
            self.switch = switch
        return m
    def evalMatches(self):
        self.deb(set([]),"Am Schluss müssen wir die gesammelten Infos ablaufen und eintragen, Kreise finden, etc...","a",1)
        # Jetzt wirds trickreich...
        # Ich baue einen Pfad auf, solange es Kanten in Reichweite gibt, die nicht zu einem Kreis gehören.
        # Wenn ich zu einem Knoten komme, den ich schon im Pfad habe, dann markiere ich alle Kanten des Pfad als Kreiskanten (link.circle)
        # Wenn ein Kreisknoten im Pfad ist (path.circle), dann reicht ein weiterer Kreisknoten um den Pfad als Kreis zu markieren
        #print self.opt.nodeGuids.keys()
        
        self.path = {}
        self.depth = 0
        for startSw in self.opt.nodeGuids.values():
            if type(startSw) is libTopology.parseNode and startSw.isSwitch():
                self.deb(startSw.getLids(),"Starte: %s" % (startSw),'l',1)
                self.actP = libTopology.thePath(self.opt)
                startSw.seen = True
                self.recursiv(startSw)
                self.deb(startSw.getLids(),"Ende: %s" % (startSw),'l',1)
                break
    def evalHistory(self):
        query = """SELECT s_id, s_name, s_state_id, n_id, n_name, n_state_id,
                            p_id, p_int, p_state_id
                    FROM nodes NATURAL JOIN ports NATURAL JOIN systems
                    ORDER BY s_id,n_id,p_id"""
        res = self.db.sel(query)
        res.reverse()
        prev_s_id = False
        prev_n_id = False
        prev_n_name = False
        prev_p_id = False
        p_stats = set([])
        n_stats = set([])
        while True:
            if len(res)>0:
                row = res.pop()
            (s_id, s_name, s_state_id, n_id, n_name, n_state_id, p_id, port, p_state_id) = row
            p_status = self.stateIds[p_state_id]
            n_status = self.stateIds[n_state_id]
            s_status = self.stateIds[s_state_id]
            if not prev_n_id:
                # Beim ersten Lauf setzen wir die IDs initial
                prev_s_id   = s_id
                prev_n_id   = n_id
                prev_p_id   = p_id
                prev_n_name     = n_name
                prev_n_status   = n_status
            if n_id==prev_n_id:
                # Noch im gleichen Node
                p_stats.add(p_status)
                prev_p_id   = p_id
            else:
                n_state_new = self.eval_states(prev_n_id, prev_n_name, prev_n_status,p_stats)
                p_stats     = set([p_status])
                prev_n_id   = n_id
                prev_n_name     = n_name
                prev_n_status   = n_status
                prev_p_id   = p_id
            if len(res)==0:
                n_state_new = self.eval_states(n_id, n_name, n_status, p_stats)
                break
            self.log.debug("%-10s: N:%-5s->%-5s || P:%-5s" % (n_name,prev_n_status,n_status,p_status),2)
    def eval_states(self,prev_n_id, prev_n_name, prev_n_status, p_stats):
        if prev_n_name=='node1':
            print prev_n_name, prev_n_status, p_stats
        if set(['chk']) == p_stats:
            # if all links are not seen anymore, the node is doomed
            n_state_new = self.stateNames['fail']
        elif 'chk' in p_stats:
            n_state_new = self.stateNames['deg']
        elif set(['ok']) == p_stats:
            n_state_new = self.stateNames['ok']
        elif set(['new']) == p_stats:
            if prev_n_status not in ('new'):
                n_state_new = self.stateNames['ok']
            else:
                n_state_new = self.stateNames['new']
        else:
            n_state_new = self.stateNames['nok']
        self.db.setNodeState(n_state_new,prev_n_id,"Event?")
        return n_state_new
        
    def eval_link_state(self):
        query = ""
        
    def recursiv(self,node):
        kinder = [x.name for x,y in node.nLinks.items()]
        self.deb(node.getLids(),"Neue Rekursion von '%s' mit Kindern '%s'" % (node.name, ",".join(kinder)),'l',1)
        self.actP.addNode(node)
        for child,links in node.nLinks.items():
            s_lids = node.getLids()
            s_lids |= child.getLids()
            self.deb(s_lids, "Betrachte Kind '%s' mit Verbindungen: " % (child),'l',1)
            for link in links:
                self.deb(link.getLids(),link,'l',1)
            if not child.isSwitch():
                node.comp_cnt += 1
                self.deb(child.getLids(),"%s ist kein Switch, weiter" % child.name,'l',2)
                continue
            if child.s_id!=node.s_id:
                node.extSw_cnt += 1
            node.sw_cnt += 1
                
            if self.actP.linkIn(links):
                self.deb(link.getLids(),"%s - Link schon drin %s" % (link.getLids(), [link.__str__() for link in links]),'l',1)
                continue
            if child.seen:
                self.deb(child.getLids(),"%s Kind '%s' über Link '%s' schon gesehen >> %s" % ("#"*self.depth,child,links,self.actP),'l',2)
                self.actP.addLinks(links)
                self.actP.flush(child)
                ## Zwei Moeglichkeiten:
                if not True: #child.circle:
                    self.deb(child.getLids(),"Neuer Kreis schliesst sich",'l',l)
            else:
                # Wenn wir momentan in keinem Circle sind, dann ist alles OK
                self.depth += 1
                s_lids = child.getLids()
                if self.opt.lids:
                    for link in links:
                        s_lids |= link.getLids()
                self.deb(s_lids,"%-10s S %-10s über %s >> %s" % ("#"*self.depth,child,links,self.actP),'l',2)
                self.actP.addLinks(links)
                # FIXME: Damit script mehrfach aufgerufen werden kann, habe ich die Zeile auskommentiert.
                #child.seen = True
                self.recursiv(child)
                self.deb(child.getLids(),"%-10s E %-10s >> %s" % ("#"*self.depth,child,self.actP),'l',2)
                # Wenn der circleStart am Ende des Pfades ist, dann ist der Kreis zu Ende
                self.actP.rmLink(links)
                self.depth -= 1
        # Wenn die Rekursion für aktuellen Knoten endet
        self.actP.rmNode(node)
    def __str__(self):
        if   self.retEC==0: retTXT = "OK"
        elif self.retEC==1: retTXT = "WARN"
        elif self.retEC==2: retTXT = "CRIT"
        retTXT += " - %s | %s" % (", ".join(self.statusList),", ".join(self.perfList))

        # perfdata
        return retTXT
    def gui_log(self,logE):
        self.log.end("create")
        self.log.finish("create")
        self.statusList.extend(self.log.get_statusList())
        logE.set_status(", ".join(self.statusList))
        self.qnib.refresh_log()
    def addPerf(self,key,val):
        if val!='0': self.statusList.append(" %s %s" % (val,key))
        self.perfList.append("%s=%s" % (key,val))
    def getEC(self):
        return self.retEC    
    def deb(self, lids, msg,typ,deb):
        if self.opt.lids:
            if hasItems(lids,self.opt.lids):
                print msg
        elif typ=='p' and self.opt.parse and self.opt.debug>=deb:
            print msg
        elif typ=='l' and self.opt.links and self.opt.debug>=deb:
            print msg
    def dump_log(self):
        fd = open(self.log_file,"a")
        msg = "%s \n" % self.__str__()
        fd.write(msg)
        fd.close()
    def update_topo(self):
        # FIXME: Should we import here? Seems to be ugly..
        import uptopo
        uptopo.eval_topo(self.opt, self.db, self.cfg, self.log)
    def create_graphs(self):
        import create_netgraph
        create_netgraph.create(self.opt, self.db, self.cfg, self.log)
    def set_guiStuff(self,qnib):
        self.qnib = qnib
    
def gui(qnib,opt):
    from qnib_control import logC, log_entry
    
    
    logE = log_entry("Exec parse_ibnetdiscover")
    qnib.addLog(logE)
    
    cfg = libTopology.config([opt.cfgfile,],opt)
    cfg.eval()
    
    db = dbCon.dbCon(opt)
    
    log = logC(opt,qnib)
    
    (trap_dict, trap_list) = db.getTraps()
    chk = checks(db, opt, cfg, log)
    chk.set_guiStuff(qnib)
    if len(trap_dict)>0 or opt.force_uptopo:
        log.debug("%s Traps detected..." % len(trap_dict),1)
        chk.ibnetdiscover()
        chk.evalSwPorts(cfg)
        chk.evalHistory()
        chk.evalMatches()
    else:
        log.debug("No traps detected...",1)
    chk.gui_log(logE)

    
    
def main():
    # Parameter
    while True:
        options = Parameter()
        options.check()
        cfg = libTopology.config([options.cfgfile,],options)
        cfg.eval()
        log = libTopology.logC(options,"/var/log/parse_ibnetdiscover.log")
        
        db = dbCon.dbCon(options)
        
        (trap_dict, trap_list) = db.getTraps()
        chk = checks(db, options, cfg, log)
        if len(trap_dict)>0 or options.force_uptopo:
            log.debug("%s Traps detected..." % len(trap_dict),0)
            chk.ibnetdiscover()
            chk.evalSwPorts(cfg)
            chk.evalHistory()
            chk.evalMatches()
            chk.addPerf('countInsLink',db.countInsLink)
            # Should we update the topology?
            # -> A new node appears
            # -> User removed a node for good
            chk.update_topo()
        else:
            log.debug("%s Traps detected..." % len(trap_dict),0)
            
        # we sure should redraw the graph to visualize the traffic
        chk.create_graphs()
        chk.dump_log()
        # If we are not suppose to loop the script, we break
        if not options.loop:
            break
        del db
        time.sleep(int(options.loop_delay))
    ec=chk.getEC()
    sys.exit(ec)


# ein Aufruf von main() ganz unten
if __name__ == "__main__":
   main()
