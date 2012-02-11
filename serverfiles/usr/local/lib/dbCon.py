#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Bibliotheken laden
import re, os, sys, commands
from optparse import OptionParser
import pgdb, datetime


class dbCon(object):
    # Konstuktor erstellt DB-Handler fuer SID und FSMON
    def __init__(self,opt,debug=None):
        # stats
        self.db = debug
        self.opt = opt
        self.querys = 0
        self.insPK = 0
        self.commits = 0
        self.countInsLink = 0
        self.insPerfQuery = ""
        # DB-Connect
        #self.__con = pgdb.connect( host='localhost', user='postgres',database='qnib' )
        self.__con = pgdb.connect( user='postgres', database='qnib' )
        # Cursor auch
        self.__cur = self.__con.cursor()
    def convSpeed(self,speed):
        if      speed=='SDR': return 250
        elif    speed=='DDR': return 500
        elif    speed=='QDR': return 1000
    def __del__(self):
        #Destruktor kickt die DB-Handler / Cursor
        self.__cur.close()
        self.__con.close()
    def commit(self):
        if self.db: self.db.deb("Commit")
        self.__con.commit()
        self.commits += 1
    def ins(self,query,debug=3):
        self.querys += 1
        self.commit()
        if self.db: self.db.deb(query,debug)
        self.__cur.execute(query)
        self.commit()
    def sel(self,query,debug=3):
        self.querys += 1
        if self.db: self.db.deb(query,debug)
        self.commit()
        self.__cur.execute(query)
        self.commit()
        return self.__cur.fetchall()
    def selOne(self,query,debug=3):
        self.querys += 1
        if self.db: self.db.deb(query,debug)
        self.__cur.execute(query)
        return self.__cur.fetchone()
    def select(self,query,debug=3):
        self.querys += 1
        if self.db: self.db.deb(query,debug)
        self.__cur.execute(query)
        return self.__cur.fetchall()
    def getPID(self,node,pnr):
        query = "SELECT p_id FROM ports NATURAL JOIN nodes WHERE n_id='%s' AND p_int='%s'" % (node.n_id,pnr)
        res = self.sel(query)
        if len(res)==1: return res[0][0]
        raise IOError("No pid found")
    def getRows(self,table,query,debug=3):
        try:
            self.querys += 1
            return self.select(query,debug)
        except pgdb.DatabaseError,e:
            if self.db: self.db.deb(e,1)
            return [] 
    def getIns_ID(self,table,where,keys,values,debug=False):
        id = self.getIDWhere(table,where)
        if not id:
            query = "INSERT INTO %s (%s) VALUES ('%s')" % \
                        (table, ",".join(keys), "','".join(values))
            self.ins(query)
            id = self.getIDWhere(table,where)
        return id
    def selNodeGUID(self,n_id):
        query = "SELECT n_guid FROM nodes WHERE n_id='%s'" % n_id
        res = self.sel(query)
        return res[0][0]
    def insLink(self,src,dst,width,speed):
        query = "SELECT * FROM links WHERE (src='%s' AND dst='%s') OR (src='%s' AND dst='%s')" % (dst.p_id,src.p_id,src.p_id,dst.p_id)
        res = self.sel(query)
        if len(res)==0:
            self.countInsLink += 1
            if speed=="QDR":    speed="1000"
            elif speed=="DDR":  speed="500"
            elif speed=="SDR":  speed="250"
            query = "INSERT INTO links (src,dst,width,speed) VALUES ('%s','%s','%s','%s')" % \
                    (src.p_id,dst.p_id,width,speed)
            self.exe(query)
            l_id = self.getIDWhere('links',"src='%s' AND dst='%s'" % (src.p_id,dst.p_id))
            return l_id         
        elif len(res)==1:
            pass
        else:
            raise IOError("Multiple Eintraege der Rueckrichtung")
    def linkSetCircle(self,src,dst,cir_id=0):
        (sNode,sPort) = src
        (dNode,dPort) = dst
        query = "SELECT * FROM setLinkCircle('%s','%s','%s')" % (cir_id, sNode.n_id,dNode.n_id)
        self.exe(query)
    def upsertPort(self,p_obj):
        p_id   = self.getIDWhere("ports","n_id='%s' and p_int='%s'" % (p_obj.n_id,p_obj.p_int))
        if not p_id:
            query = "INSERT INTO ports (n_id,p_int,p_ext) VALUES  ('%s','%s','%s')" % (p_obj.n_id,p_obj.p_int,p_obj.p_ext)
            self.ins(query)
            p_id   = self.getIDWhere("ports","n_id='%s' and p_int='%s'" % (p_obj.n_id,p_obj.p_int))
        else:
            query = "UPDATE ports SET p_status='ok',p_ext='%s' WHERE p_id='%s' AND p_status='chk'" % (p_obj.p_ext,p_id)
            self.ins(query)
        return p_id
    def getIDWhere(self,table,where,debug=False):
        self.commit()
        if table=='chassis': idName='c_id'
        elif table=='systems': idName='s_id'
        elif table=='nodes': idName='n_id'
        elif table=='ports': idName='p_id'
        elif table=='nodetypes': idName='nt_id'
        elif table=='sinces': idName='si_id'
        elif table=='dumptimes': idName='dt_id'
        elif table=='links': idName='l_id'
        elif table=='circles': idName='cir_id'
        else:
            print "Fuer '%s' wurde die id nicht definiert" % table
            sys.exit()
        query = "SELECT %s FROM %s WHERE %s" % (idName,table,where)
        if debug: print query
        id = self.select(query)
        if id: return id[0][0]
        else:  return None
    def update(self,query,debug=3):
        self.commit()
        self.exe(query,debug)
        self.commit()
    def exe(self,query,debug=3):
        if self.db: self.db.deb(query,debug)
        self.__cur.execute(query)
        self.querys += 1
        self.commit()
    def updatePerfcache(self,portid,pkId,perf):
        query = "select upsert_perfcache('%s', '%s','%s')" % (portid,pkId,int(perf))
    def deltaLoop(self,query,debug=3):
        L = True
        ret = []
        while L:
            self.commit()
            res = self.select(query,debug)
            if not res: L=False
            else:
                ret.append(res[0])
            if len(ret)>=9: L = False
        return ret
    def getPerfkeys(self):
        query = "SELECT pk_id,pk_name FROM perfkeys"
        res = self.sel(query)
        ret = {}
        for item in res: ret[item[1]] = item[0]
        return ret
    def updatePerfkeys(self,perfkey):
        query = "INSERT INTO perfkeys (pk_name) VALUES ('%s')" % perfkey
        self.ins(query)
        return self.getPerfkeys()
    def addPerfkeys(self,pdId,cId,val):
        self.insPK += 1
        self.insPerfQuery += """
            INSERT INTO counter_store (pd_id,pk_id,cs_val) VALUES ('%s','%s','%s');
            """% (pdId,cId,val)
    def insPerfkeys(self):
        self.ins(self.insPerfQuery)
        self.insPerfQuery = ""
    def dc_getNodeID(self,guid,name,sId):
        query = "SELECT getInsID_dc_nodes('%s','%s','%s')" % (guid,name,sId)
        return self.sel(query)[0][0]
    def dc_insPort(self,dc_nId,port):
        query = "SELECT getInsID_dc_ports('%s','%s')" % (dc_nId,port)
        return self.sel(query)[0][0]
    def getPortID(self,nId,port):
        query = "SELECT getPortID('%s','%s')" % (nId,port)
        return self.sel(query)[0][0]
    def getPortidDump(self,pId,pkId,dId):
        query = "select * from getInsID_portidDumps(%s,%s,%s)" % (pId,pkId,dId)
        if self.db: self.db.deb(query,debug)
        return self.sel(query)[0][0]
    def insGet_ID(self,table,where):
        query = "INSERT INTO %s (%s) VALUES ('%s')" % \
            (table, key, val)
        self.ins(query)
        id = self.getIDWhere(table,where)
        return id
    def getLocality(self,lid):
        query = "SELECT * FROM getLocality('%s')" % lid
        return self.sel(query)[0]
    def perfCacheEval(self):
        S = int(datetime.datetime.now().strftime("%s"))
        query = """SELECT nt_id,n_id,p_id,pk_id,pc_val,pkt_id,pk_name,p_guid,lid,dlid,port,dport,extport,width,speed, uplink, p_notseen,s_id,n_guid,nt_name
                            FROM perfcache NATURAL JOIN perfkeys NATURAL JOIN ports NATURAL JOIN nodes NATURAL JOIN nodetypes ORDER BY pk_name"""
        # dadurch wird sichergestellt, dass xmit_wait am ende auftaucht - wenn xmit_pkts schon eingetragen ist
        res = self.sel(query)
        pc = {'locality':0,'xmit_congMAX':0}
        for row in res:
            (nt_id,n_id,p_id,pk_id,pc_val,pkt_id,pk_name,p_guid,lid,dlid,port,dport,extport,width,speed, uplink, p_notseen,s_id,n_guid,nt_name) = row
            pKey = "%s:%s"%(port,dport)
            if not pc.has_key(lid):
                (up,down,upIn,downOut,upOut,downIn) = self.getLocality(lid)
                pc[lid]         = {'locUp':up,'locDown':down,'locUpIn':upIn,'locDownOut':downOut,'locUpOut':upOut,'locDownIn':downIn}
            if not pc[lid].has_key(dlid):
                pc[lid][dlid]   = { # Es werden die Keys mitgezogen, die auf die jeweiligen Caches passen,initialisiert mit akt. wert
                                    'links':set([]),
                                    'bwMAX':pKey,   # port-key der die maxBW hat
                                    'bwMIN':pKey,   # minBW
                                    "%sMAX"%pk_name:pKey,   # maximalwert des aktuell betrachteten performancekeys
                                    "%sMIN"%pk_name:pKey,   # minwert "
                                    pKey:{'bw':int(speed)*int(width),pk_name:pc_val}, # das ist der eigentliche Datencontainer
                                }
            else:
                pc[lid][dlid]['links'].add(pKey)
                if pk_name=="xmit_wait":
                    src = pc[lid][dlid]
                    pkMAX = "xmit_waitMAX"
                    pkMIN = "xmit_waitMIN"
                    xwMAX = "xmit_congMAX"
                    xwMIN = "xmit_congMIN"
                    if src[pKey]['xmit_pkts']!=0:
                        xw  = float(pc_val)*1000/src[pKey]['xmit_pkts']
                    else:
                        xw  = 0.0
                    pc[lid][dlid][pKey][pk_name]     = pc_val
                    pc[lid][dlid][pKey]["xmit_cong"] = xw
                    
                    if not src.has_key(pkMIN):
                        pc[lid][dlid][pkMIN]   = pKey
                    if not src.has_key(pkMAX):
                        pc[lid][dlid][pkMAX]   = pKey
                    if pc_val>src[src[pkMAX]]:  pc[lid][dlid][pkMAX]   = pKey
                    if pc_val<src[src[pkMIN]]:  pc[lid][dlid][pkMIN]   = pKey
                    
                    if not src.has_key(xwMIN):
                        pc[lid][dlid][xwMIN]   = pKey
                    if not src.has_key(xwMAX):
                        pc[lid][dlid][xwMAX]   = pKey
                    if xw>src[src[xwMAX]]:  pc[lid][dlid][xwMAX]   = pKey
                    if xw<src[src[xwMIN]]:  pc[lid][dlid][xwMIN]   = pKey
                    if xw>pc[xwMAX]:        pc[xwMAX]   = xw
                else:
                    src = pc[lid][dlid]
                    pkMAX = "%sMAX"%pk_name
                    pkMIN = "%sMIN"%pk_name
                    
                    if not src.has_key(pkMIN):
                        pc[lid][dlid][pkMIN]   = pKey
                    if not src.has_key(pkMAX):
                        pc[lid][dlid][pkMAX]   = pKey
                    
                    if not pc[lid][dlid].has_key(pKey):
                        pc[lid][dlid][pKey]    = {}
                    pc[lid][dlid][pKey][pk_name] = pc_val
                    
                    bw = int(speed)*int(width)
                    if (not src.has_key('bwMAX')) or bw>src[src['bwMAX']]['bw']:
                        pc[lid][dlid]['bwMAX'] = pKey
                    if (not src.has_key('bwMIN')) or bw<src[src['bwMIN']]['bw']:
                        pc[lid][dlid]['bwMIN'] = pKey
                    if (not src.has_key(pkMAX)) or pc_val>src[src[pkMAX]][pk_name]:
                        pc[lid][dlid][pkMAX]   = pKey
                    if (not src.has_key(pkMIN)) or pc_val<src[src[pkMIN]][pk_name]:
                        pc[lid][dlid][pkMIN]   = pKey
        E = int(datetime.datetime.now().strftime("%s"))
        self.pc = pc
        self.evalTime = E-S
    def pcGetPort(self,lid,dlid):
        src = self.pc[lid][dlid]
        dst = self.pc[dlid][lid]
        bw  = src[src['bwMAX']]['bw']
        try: sD  = src[src['xmit_dataMAX']]['xmit_data']
        except KeyError:
            if self.opt.debug>=2: print "Keine Daten fuer xmit_dataMax: %s" % src
            sD = 0
        try: dD  = dst[dst['xmit_dataMAX']]['xmit_data']
        except KeyError:
            if self.opt.debug>=2: print "Keine Daten fuer xmit_data: %s" % dst[dst['xmit_dataMAX']]
            dD = 0
        res = (bw, sD,dD)
        return res
    def pcGetLinks(self,lid,dlid):
        src = self.pc[lid][dlid]
        dst = self.pc[dlid][lid]
        bw = src[src['bwMAX']]['bw']
        res = []
        for link in src['links']:
            (s,d) = link.split(":")
            sP = src["%s:%s" % (s,d)]['xmit_pkts']
            sC = src["%s:%s" % (s,d)]['xmit_cong']
            dP = dst["%s:%s" % (d,s)]['xmit_pkts']
            try: dC = dst["%s:%s" % (d,s)]['xmit_cong']
            except: dC = 0
            tmp = (sP,sC,link,dP,dC)
            res.append(tmp)
        return res
    def pcGetLink(self,lid,dlid):
        src = self.pc[lid][dlid]
        dst = self.pc[dlid][lid]
        max = self.pc['xmit_congMAX']
        sC = src[src['xmit_congMAX']]['xmit_cong']
        try: dC = dst[dst['xmit_congMAX']]['xmit_cong']
        except: # wenn das auf die Schnautze faellt, dann ist es ein Host (keine Congestion moeglich)
            dC = 0
        res = (max,sC,dC)
        return res
    def pcGetLocality(self,lid):
        up      = self.pc[lid]['locUp']
        down    = self.pc[lid]['locDown']
        upIn    = self.pc[lid]['locUpIn']
        downOut = self.pc[lid]['locDownOut']
        upOut   = self.pc[lid]['locUpOut']
        downIn  = self.pc[lid]['locDownIn']
        return up,down,upIn,downOut,upOut,downIn
