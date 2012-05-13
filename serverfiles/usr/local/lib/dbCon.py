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
        self.__con = pgdb.connect( user='postgres', database='qnib' )
        # Cursor auch
        self.__cur = self.__con.cursor()
        
        self.stateIds  = self.getStatesId()
        self.stateNames= self.getStatesName()
    def convSpeed(self,speed):
        if      speed=='SDR': return 250
        elif    speed=='DDR': return 500
        elif    speed=='QDR': return 1000
    def __del__(self):
        #Destruktor kickt die DB-Handler / Cursor
        self.__cur.close()
        self.__con.close()
    def close(self,name=None):
        self.__cur.close()
        self.__con.close()
        if name:
            print "%s> everything closed" % name
    def commit(self):
        if self.db: self.db.deb("Commit")
        self.__con.commit()
        self.commits += 1
    def exe(self, query, debug=3):
        self.querys += 1
        self.commit()
        if self.db:
            self.db.deb(query, debug)
        self.__cur.execute(query)
        self.commit()
    def ins(self,query,debug=3):
        self.querys += 1
        self.commit()
        if self.db: self.db.deb(query,debug)
        self.__cur.execute(query)
        self.commit()

    def getLinkList(self,s_id=False):
        """ List all Links within the fabric """
        query = """SELECT   l.l_id,
                            p1.p_lid,
                            p1.p_id,
                            p1.p_int,
                            n1.n_id,
                            n1.n_name,
                            n1.n_guid,
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
                            n2.n_guid,
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
                                s2.c_id = c2.c_id"""
        if s_id:
            query += "AND (s1.s_id='%s' OR s2.s_id='%s')" % (s_id, s_id)
        return self.getLinkListRes(query)

    def getLinkListRes(self, query):
        """ Creates dictonary out of query """
        res = self.sel(query)
        back = []
        for row in res:
            acc = {}
            (l_id, s_lid, s_p_id, s_port, s_nid, s_nname, s_nguid, s_n_state_id,
             s_ntname, s_sname, s_sguid, s_sid, s_cname, s_cid, circle, d_cid, \
             d_cname, d_sid, d_sguid, d_sname, d_ntname, d_n_state_id, \
             d_nguid, d_nname, d_nid, d_port, d_p_id, d_lid) = row

            acc['l_id'] = l_id
            acc['s_p_lid'] = s_lid
            acc['s_p_id'] = s_p_id
            acc['s_p_int'] = s_port
            acc['s_n_id'] = s_nid
            acc['s_n_name'] = s_nname
            acc['s_n_guid'] = s_nguid
            acc['s_n_state_id'] = s_n_state_id
            acc['s_nt_name'] = s_ntname
            acc['s_s_name'] = s_sname
            acc['s_c_name'] = s_cname
            acc['s_s_id'] = s_sid
            acc['s_c_id'] = s_cid
            acc['s_s_guid'] = s_sguid
            acc['circle'] = circle
            acc['d_s_guid'] = d_sguid
            acc['d_c_id'] = d_cid
            acc['d_s_id'] = d_sid
            acc['d_c_name'] = d_cname
            acc['d_s_name'] = d_sname
            acc['d_nt_name'] = d_ntname
            acc['d_n_state_id'] = d_n_state_id
            acc['d_n_guid'] = d_nguid
            acc['d_n_name'] = d_nname
            acc['d_n_id'] = d_nid
            acc['d_p_int'] = d_port
            acc['d_p_id'] = d_p_id
            acc['d_p_lid'] = d_lid
            back.append(acc)
        return back

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

    def getPID(self,node,pnr):
        query = "SELECT p_id FROM ports NATURAL JOIN nodes WHERE n_id='%s' AND p_int='%s'" % (node.n_id,pnr)
        res = self.sel(query)
        if len(res)==1: return res[0][0]
        raise IOError("No pid found")

    def getSystems(self):
        """ gets all nodes out of the system """
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
                                s1.c_id=c1.c_id"""
        res = self.sel(query)
        return res
    def getRows(self,table,query,debug=3):
        try:
            self.querys += 1
            return self.sel(query,debug)
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
    def insLink(self, src, dst, width, speed):
        query = """SELECT l_id, src, dst, width, speed, uplink, l_status, circle
                    FROM links WHERE (src='%s' AND dst='%s')
                               OR (src='%s' AND dst='%s')""" % \
                    (dst.p_id,src.p_id,src.p_id,dst.p_id)
        res = self.sel(query)
        if speed=="QDR":    speed="1000"
        elif speed=="DDR":  speed="500"
        elif speed=="SDR":  speed="250"
        if len(res)==0:
            self.countInsLink += 1
            query = "INSERT INTO links (src,dst,width,speed) VALUES ('%s','%s','%s','%s')" % \
                    (src.p_id,dst.p_id,width,speed)
            self.exe(query)
            l_id = self.getIDWhere('links',"src='%s' AND dst='%s'" % (src.p_id,dst.p_id))
            return l_id         
        elif len(res)==1:
            (db_l_id, db_src, db_dst, db_width, db_speed, db_uplink, db_l_status, db_circle) = res[0]
            if db_speed!=speed:
                query = "UPDATE links SET speed='%s' WHERE l_id='%s'" % (speed, db_l_id)
                self.update(query)
            if db_width!=width:
                query = "UPDATE links SET width='%s' WHERE l_id='%s'" % (width, db_l_id)
                self.update(query)
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
            query = "INSERT INTO ports (n_id,p_int,p_ext,p_lid) VALUES  ('%s','%s','%s','%s')" % (p_obj.n_id,p_obj.p_int,p_obj.p_ext,p_obj.lid)
            self.ins(query)
            p_id   = self.getIDWhere("ports","n_id='%s' and p_int='%s'" % (p_obj.n_id,p_obj.p_int))
        else:
            # TODO: ugly, because the p_state_id is hardwired
            query = """UPDATE ports SET p_state_id='%s',p_ext='%s',p_lid='%s'
                        WHERE p_id='%s' AND p_state_id='%s'""" % \
                        (self.stateNames['ok'], p_obj.p_ext,\
                         p_obj.lid, p_id,self.stateNames['chk'])
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
        id = self.sel(query)
        if id:
            if debug: print id[0][0]
            return id[0][0]
        else:  return None
    def update(self,query,debug=3):
        self.commit()
        self.exe(query,debug)
        self.commit()
    def exe(self,query,debug=3):
        if self.db: self.db.deb(query,debug)
        self.commit()
        self.__cur.execute(query)
        self.querys += 1
        self.commit()
    def updatePerfcache(self,portid,pkId,perf):
        query = "SELECT upsert_perfcache('%s', '%s','%s')" % (portid,pkId,int(perf))
    def deltaLoop(self,query,debug=3):
        L = True
        ret = []
        while L:
            self.commit()
            res = self.sel(query,debug)
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
        query = "SELECT * FROM getInsID_portidDumps(%s,%s,%s)" % (pId,pkId,dId)
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
            acc[state_id] = state_name
        return acc
    def setNodeState(self,n_state_new,n_id,event):
        # TODO: should be a postgres function
        query = "SELECT n_state_id,state_name FROM nodes JOIN states ON n_state_id=state_id WHERE n_id='%s'" % n_id
        res = self.selOne(query)
        n_state_old = res[0]
        if self.stateNames['new']==n_state_old==n_state_new:
            query = "INSERT INTO node_history (n_id,nh_state_id,nh_message) VALUES ('%s','%s','new');" % (n_id,n_state_new)
            self.ins(query)
        elif int(n_state_new)!=int(n_state_old):
            query =  "UPDATE nodes SET n_state_id='%s' WHERE n_id='%s';" % (n_state_new,n_id)
            query += "INSERT INTO node_history (n_id,nh_state_id,nh_message) VALUES ('%s','%s','%s->%s');" % (n_id,n_state_new,self.stateIds[n_state_old],self.stateIds[n_state_new])
            self.ins(query)
    def setPortState(self,p_id,p_state_new):
        query = "SELECT p_state_id FROM ports WHERE p_id='%s'" % p_id
        p_state_old = self.selOne(query)[0]
        if int(p_state_new)!=int(p_state_old) and self.stateIds[p_state_old]!='chk':
            query = "UPDATE ports SET p_state_id='%s' WHERE p_id='%s';" % (p_state_new,p_id)
            self.ins(query)
            query = " INSERT INTO port_history (p_id,ph_state_id,ph_message) VALUES ('%s','%s','%s->%s');" % (p_id,p_state_new,p_state_old,p_state_new)
            self.ins(query)
    def getTraps(self):
        query =  """SELECT
                        trap_id, trap_type, trap_event, trap_lid, trap_time
                    FROM traps"""
        res = self.sel(query)
        trap_list = []
        ids = []
        trap_dict = {}
        for row in res:
            t_id   = int(row[0])
            t_type  = int(row[1])
            t_event = int(row[2])
            t_lid   = int(row[3])
            t_time  = row[4]
            ids.append(str(t_id))
            if t_type==1:
                trap_list.append([
                            t_id,
                            t_type,
                            t_event,
                            t_lid,
                            t_time,
                           ])
                if not trap_dict.has_key(t_lid):
                    trap_dict[t_lid] = set([])
                trap_dict[t_lid].add(t_event)
                    
        if len(ids)>0:
            query = "DELETE FROM traps WHERE trap_id in ('%s')" % "','".join(ids)
            self.exe(query)
        return (trap_dict,trap_list)