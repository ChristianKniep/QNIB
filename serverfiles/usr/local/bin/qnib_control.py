#!/usr/bin/env python
#-*- coding: utf-8 -*-

import gtk
import pango
import sys
import copy
import time

sys.path.append("/root/QNIB/serverfiles/usr/local/lib/")
import libibsim
sys.path.append("/root/QNIB/serverfiles/usr/local/bin/")
import parse_ibnetdiscover
import uptopo
import create_netgraph

class logC(object):
    def __init__(self, opt, qnib):
        self.opt    = opt
        self.qnib   = qnib
        self.statusList = []
        self.perfList   = []
        self.retEC = 0
        self.s = {}
        self.res  = {}
    def addPerf(self,key,val):
        self.perfList.append("%s=%s" % (key,val))
        if val!=0:
            self.statusList.append("%sms %s" % (val,key))
    def __str__(self):
        if   self.retEC==0: retTXT = "OK"
        elif self.retEC==1: retTXT = "WARN"
        elif self.retEC==2: retTXT = "CRIT"
        retTXT += " - %s | %s" % (", ".join(self.statusList),", ".join(self.perfList))
        return retTXT
    def get_status(self):
        return ", ".join(self.statusList)
    def getEC(self):
        return self.retEC
    def start(self,stat):
        if not self.res.has_key(stat): self.res[stat] = 0
        self.s[stat] = time.time()
    def end(self,stat):
        e = time.time()
        self.res[stat] += int((e - self.s[stat])*1000)
        self.s[stat] = 0
    def finish(self,stat):
        self.addPerf(stat,self.res[stat])
        self.res[stat] = 0
    def debug(self, msg, deb=3):
        if self.opt.debug>=deb:
            logE = log_entry(msg)
            self.qnib.addLog(logE)
            self.qnib.refresh_log()
    def get_statusList(self):
        return self.statusList
class log_entry(object):
    def __init__(self,desc):
        self.desc   = desc.strip()
        self.status = ""
    def set_status(self,status):
        self.status = status.strip()
    def set_desc(self,desc):
        self.desc = desc.strip()
    def __str__(self):
        if self.status!="":
            res = "%s : %s" % (self.desc.ljust(25),self.status)
        else:
            res = self.desc
        return res

class MyApp(object):
    def __init__(self, opt):
        self.opt = opt
        self.builder = gtk.Builder()
        self.builder.add_from_file("/root/QNIB/serverfiles/usr/local/etc/ibsim.ui")
        self.builder.connect_signals(self)
        self.ibs = libibsim.ibsim("/root/QNIB/serverfiles/test/netlist.clos5")
        self.log_win = self.builder.get_object("log")
        self.log_buffer = self.log_win.get_buffer()
        font_desc=pango.FontDescription('Courier 10')
        self.log_win.modify_font(font_desc)

        logE = log_entry("")
        self.log_text = [logE]*10
        self.start_services()
    def run(self):
        try:
            gtk.main()
        except KeyboardInterrupt:
            pass
    def quit(self):
        self.ibsim(False)
        self.opensm(False)
        gtk.main_quit()
    def start_services(self):
        """ We are pressing the butons and using the callback functions """
        ibsim_but = self.builder.get_object("ibsim")
        ibsim_but.set_active(True)
        ibsim_but = self.builder.get_object("opensm")
        ibsim_but.set_active(True)
    def start_service(self,opt):
        if opt.get_name()=='ibsim':
            self.ibsim(opt.get_active())
        elif opt.get_name()=='opensm':
            self.opensm(opt.get_active())
    def ibsim(self,start=True):
        if start: logE = log_entry("Starting ibsim")
        else: logE = log_entry("Stoping ibsim")
        self.addLog(logE)
        self.ibs.service_ibsim(logE, start)
        self.refresh_log()
    def opensm(self,start=True):
        if start: logE = log_entry("Starting opensm")
        else: logE = log_entry("Stoping opensm")
        self.addLog(logE)
        self.ibs.service_opensm(logE, start)
        self.refresh_log()
    def addLog(self,logE):
        self.log_text.append(logE)
        self.refresh_log()
    def refresh_log(self):
        logList = [x.__str__() for x in self.log_text[-10:]]
        logList.reverse()
        self.log_buffer.set_text("\n".join(logList))
    def node_toggled(self,opt):
        if opt.get_active():
            logE = log_entry("Relink %s" % opt.get_name())
            self.addLog(logE)
            res = self.ibs.relink(logE, opt.get_name())
        else:
            logE = log_entry("Unlink %s" % opt.get_name())
            self.addLog(logE)
            res = self.ibs.unlink(logE, opt.get_name())
        self.refresh_log()
    def exec_script(self,opt):
        script = opt.get_name()
        if script=="parse_ibnetdiscover":
            parse_ibnetdiscover.gui(self,self.opt)
        elif script=="uptopo":
            uptopo.gui(self,self.opt)
        elif script=="create_netgraph":
            create_netgraph.gui(self,self.opt)
        if script=="complete_run":
            parse_ibnetdiscover.gui(self,self.opt)
            uptopo.gui(self,self.opt)
            create_netgraph.gui(self,self.opt)
        
    def on_window1_delete_event(self, *args):
        self.quit()


if __name__ == '__main__':
    options = parse_ibnetdiscover.Parameter()
    options.check()
    app = MyApp(options)
    app.run()
