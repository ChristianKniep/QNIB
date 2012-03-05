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
            command = [self.bin,"-c","1000","-s",self.topo_file]
            self.ibs_proc = subprocess.Popen(command, shell=False, stderr=None,stdout=subprocess.PIPE,stdin=subprocess.PIPE)
            logE.set_status("OK")
        else:
            self.ibs_proc.kill()
            logE.set_status("OK")
    def service_opensm(self, logE, start=True):
        if start:
            cmd = ["/usr/local/sbin/opensm","-F","/etc/opensm.conf"]
            self.sm_proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            logE.set_status("OK")
        else:
            self.sm_proc.kill()
            logE.set_status("OK")
    def unlink(self, logE, host, port=False):
        if port:
            node = "\"%s\"[%s]" % (host,port)
        else:
            node = "\"%s\"" % host
        line = "unlink %s\n" % node
        logE.set_desc("Unlink %s" % node)
        self.ibs_proc.stdin.write(line)
        logE.set_status("OK")
    def relink(self,logE,host,port=False):
        if port:
            node = "\"%s\"[%s]" % (host,port)
        else:
            node = "\"%s\"" % host
        logE.set_desc("Relink %s" % node)
        line = "relink %s\n" % node
        self.ibs_proc.stdin.write(line)
        logE.set_status("OK")
