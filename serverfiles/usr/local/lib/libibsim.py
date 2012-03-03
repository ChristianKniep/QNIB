import pexpect
import sys
import re
import subprocess
import time
import datetime

class ibsim(object):
    def __init__(self,topo_file,bin="/usr/bin/ibsim"):
        self.topo_file  = topo_file
        self.bin        = bin
        self.log_file   = "/var/log/ibsom.log"
    def log(self,msg):
        zeit = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        fd = open(self.log_file,"a")
        fd.write("%s: %s\n" % (zeit,msg))
        fd.close()
    def service_ibsim(self, logE, start=True):
        if start:
            self.child = pexpect.spawn("%s -c 1000 -s %s" % (self.bin,self.topo_file))
            logE.set_status("OK")
        else:
            self.child.kill(0)
            logE.set_status("OK")
    def service_opensm(self, logE, start=True):
        if start:
            cmd = ["/usr/local/sbin/opensm","-F","/etc/opensm.conf"]
            self.sm_proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            logE.set_status("OK")
        else:
            self.sm_proc.kill()
    def unlink(self, logE, host, port=False):
        self.child.expect("sim> ",timeout=4)
        if port:
            node = "\"%s\"[%s]" % (host,port)
        else:
            node = "\"%s\"" % host
        errc = self.child.sendline("unlink %s\r" % node)
        if errc==18:
            logE.set_desc("Unlink Host %s" % node)
            self.log("unlink switch %s finished" % host)
            logE.set_status("OK")
        elif errc==19:
            logE.set_desc("Unlink Edge %s" % node)
            self.log("unlink switch %s finished" % host)
            logE.set_status("OK")
        elif errc==17:
            logE.set_desc("Unlink Spine %s" % node)
            self.log("unlink switch %s finished" % host)
            logE.set_status("OK")
        else:
            self.log("unlink '%s' ended with abnormal rc '%s'" % (host,errc))
            logE.set_status("FAILED - EC:%s" % errc)
    def relink(self,logE,host,port=False):
        self.child.expect("sim> ",timeout=4)
        if port:
            node = "\"%s\"[%s]" % (host,port)
        else:
            node = "\"%s\"" % host
        logE.set_desc("Relink %s" % node)
        errc = self.child.sendline("relink %s\r" % node)
        if errc==19:
            logE.set_desc("Relink Edge %s" % node)
            logE.set_status("OK")
        elif errc==18:
            logE.set_desc("Relink Host %s" % node)
            logE.set_status("OK")
        elif errc==17:
            logE.set_desc("Relink Spine %s" % node)
            logE.set_status("OK")
        else:
            self.log("relink '%s' ended with abnormal rc '%s'" % (host,errc))
            logE.set_status("FAILED - EC:%s" % errc)
