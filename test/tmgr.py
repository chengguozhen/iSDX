#!/usr/bin/python

#  Author:
#  Marc Pucci (Vencore Labs)

# tmgr - traffic manager - controls a constellation of traffic nodes
# to gen and recv traffic from / to specific bound interfaces and ports

import sys
import json
import socket
import random
import string
import platform
import os
import subprocess
import traceback
import time
import shlex

np = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if np not in sys.path:
    sys.path.append(np)
import util.log

config = {}     # JSON configuration data
hosts = {}
tests = {}
cmdfuncs = {}
commands = {}
regressions = {}


# friendly logger - prints to stdout and logs.
# TODO check to see if logging is actually happening and print only if so

class flog ():
    def __init__(self, name):
        self.logger = util.log.getLogger(name)
    def info(self, m):
        print m
        self.logger.info(m)
    def debug(self, m):
        print m
        self.logger.debug(m)
    def error(self, m):
        print m
        self.logger.error(m)

log = flog('TMGR')
log.info("Starting TMGR")

def main (argv):
    global config, hosts, tests, cmdfuncs, commands, regressions
    
    if len(argv) < 2:
        log.error('usage: tmgr config.json [ commands ]')
        exit()
    
    cfile = argv[1]
    
    try:
        f = open(cfile)
    except Exception, e:
        log.error('cannot open configuration file: ' + cfile + ': ' + repr(e))
        exit()
        
    try:    
        config = json.load(f)
    except Exception, e:
        log.error('bad data in configuration file: ' + cfile + ': ' + repr(e))
        exit()
    f.close()
    
    try:
        hosts = config["hosts"]
    except:
        log.error('no host data in configuration file: ' + cfile)
        exit()
    
    try:
        tests = config["tests"]
    except:
        log.error('no test data in configuration file: ' + cfile)
        exit()
        
    try:
        regressions = config["regressions"]
    except:
        log.error('no regression test in configuration file: ' + cfile)
        exit()
        
    commands = config.get('commands', {})
       
    cmdfuncs = {
        'reset': (reset, hosts, 'reset (close) listeners - takes a few seconds to take effect'),
        'z': (reset, hosts, None),
        'kill': (kill, hosts, 'terminate traffic nodes'),
        'k': (kill, hosts, None),
        'listener': (listener, hosts, 'start listeners on nodes with bind addr and port'),
        'l': (listener, hosts, None),
        'dump': (dump, hosts, 'dump output from hosts - mainly to see if nodes are on-line'),
        'd': (dump, hosts, None),
        'test': (test, tests, 'execute tests - send request to source node and check expected destination'),
        't': (test, tests, None),
        'rexec': (rexec, None, 'run command on remote hosts'),
        'r': (rexec, None, None),
        'exec': (run, None, 'run command on this (tmgr) host'),
        'e': (run, None, None),
        'config': (show, None, 'show json configuration'),
        'c': (show, None, None),
        'help': (usage, None, 'print this message'),
        'h': (usage, None, None),
        '?': (usage, None, None),
        'quit': (terminate, None, 'exit this manager - leave nodes intact'),
        'q': (terminate, None, None),
        'pending': (pending, hosts, 'query for any pending or completed test results'),
        'p': (pending, hosts, None),
        'regression': (regress, regressions, 'run a (multi command) regression test'),
        'reg': (regress, regressions, None)
    }
    
    if len(argv) == 2:
        while True:
            try:
                parse(raw_input("> "))
            except EOFError:
                break
            except Exception, e:
                log.error('MM:00 ERROR: ' + repr(e))
                traceback.print_exc(file=sys.stdout)
                break
    else:
        for i in range(2, len(argv)):
            parse(argv[i])
        
    log.info('MM:00 INFO: BYE')


def parse (line):
    global cmdfuncs
    
    tokens = line.split()
    n = len(tokens)
    if n == 0:
        return
    cmd = tokens[0]
    if cmd[0] == '#':
        return
    
    # search for the command
    # if there is a dictionary in the list, iterate over all the elements or all the arguments
    # else pass the entire set of arguments to the command
    
    foo = cmdfuncs.get(cmd)
    if foo != None:
        func, jset, _ = foo
        if jset is None:
            func(tokens)
            return
        if n == 1:
            for h in sorted(jset):
                func(h)
        else:
            for i in range(1, n):
                func(tokens[i])
        return

    log.error('MM:00 ERROR: unknown command: ' + cmd)
    

# connect to the cmd interface or a host
# the host must be in the json file
# if it defines cmdifc and cmdport, use them; else use defaults
# todo: cache the ifc and port

def connect (host, why):
    global config
    
    # should be either a listener host or a router host (edge-router)
    try:
        hostdata = config['hosts'][host]
    except:
        if host not in config['rhosts']:
            log.error('MM:' + host + ' ERROR: ' + why + ': Unknown host: ' + host)
            return None    
    try:
        cmdifc = hostdata['cmdifc']
        cmdport = hostdata['cmdport']
    except:
        if platform.system() == 'Windows':
            cmdifc = '127.0.0.1'
            cmdport = base36(host)
        else:
            cmdifc = '/tmp/' + host
            cmdport = 0
    
    #print 'MM:' + host + ' INFO: ' + why + ': Connecting to ' + host + ' at ' + cmdifc + ':' + str(cmdport)

    try:
        if cmdifc.find('/') >= 0:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) # @UndefinedVariable
            s.connect(cmdifc)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((cmdifc, cmdport))
    except Exception, e:
        log.error('MM:' + host + ' ERROR: ' + why + ': ' + repr(e))
        return None
    return s 
 

# grab any tnode queued data - this is usually just the result of tnode startup
    
def dump (host):
    log.info('MM:' + host + ' DUMP')
    r = generic(host, 'DUMP', 'dump\n')
    if r is not None:
        if len(r) == 0:
            log.info('MM:' + host + ' output = <None>' + r.strip())
        else:
            log.info('MM:' + host + ' output = \n' + r.strip())


# force tnode to exit

def kill (host):
    log.info('MM:' + host + ' QUIT')
    r = generic(host, 'QUIT', 'quit\n')
    if r is not None:
        log.info('MM:' + host + ' output = ' + r.strip())


# terminate all listeners on a tnode, tnode does not exit

def reset (host):
    log.info('MM:' + host + ' RESET')
    r = generic(host, 'RESET', 'reset\n')
    if r is not None:
        log.info('MM:' + host + ' output = ' + r.strip())

# execute a command locally

def run (args):
    if len(args) < 2:
        print 'MM:00 EXEC: ERROR usage: exec cmd cmd ...'
        print 'Commands are:'
        for c in sorted(commands):
            print '  ' + c + ': ' + commands[c]
        return
    
    for i in range(1, len(args)):
        cmdname = args[i]
        try:
            c = commands[cmdname]
        except:
            log.error('MM:00 ERROR: EXEC FAILED unknown or poorly specified cmd: ' + cmdname)
            continue
        log.info('MM:00 EXEC: ' + cmdname + ' cmd = ' + c)
        ca = c.split()
        try:
            p = subprocess.Popen(ca, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
        except Exception, e:
            out = ''
            err = 'Command Failed: ' + repr(e)
        r = out + err
        log.debug('MM:00 EXEC: ' + cmdname + ' output = \n' + r.strip())
    return None
    

# execute a command remotely

def rexec (args):
    if len(args) < 3:
        print 'MM:00 REXEC: ERROR usage: rexec cmd host host ...'
        print 'Commands are:'
        for c in sorted(commands):
            print '  ' + c + ': ' + commands[c]
        return
    cmdname = args[1]
    try:
        c = commands[cmdname]
    except:
        log.error('MM:00 ERROR: REXEC FAILED unknown or poorly specified cmd: ' + cmdname)
        return
    for i in range(2, len(args)):
        host = args[i]
        log.info('MM:' + host + ' REXEC ' + cmdname + ' cmd = ' + c)
        r = generic(host, 'REXEC', 'exec ' + c + '\n')
        if r is not None:
            log.debug('MM:' + host + ' REXEC ' + cmdname + ' output = \n' + r.strip())
        
        
# generic command interface to a tnode - send cmd, capture data
# return None id cannot connect or socket error
# return '' if no data

def generic (host, label, cmd):
    s = connect(host, label)
    if s == None:
        return None
    
    alldata = ''
    try:
        s.send(cmd)
        
        while True:
            data = s.recv(1024)
            if len(data) == 0:
                break
            alldata += data
            #sys.stdout.write(data)
        s.close()
    except Exception, e:
        log.error('MM:' + host + ' ERROR: ' + label + ': '+ repr(e))
        try:
            s.close()
        except:
            pass
        return None
    return alldata

 
# run a test from the json config - tell source to send to dst IP addr.
# expect result from appropriate host and interface       
 
def test (tn):
    global config
    rand = str(random.randint(1000000000, 9999999999)) # must be 10 characters
    try:
        src = config["tests"][tn]['src']
        baddr = config["tests"][tn]['baddr']
        daddr = config["tests"][tn]['daddr']
        dport = config["tests"][tn]['dport']
        xdst = config["tests"][tn]['xdst']
    except:
        log.error('MM:00 ERROR: TEST FAILED unknown or poorly specified test: ' + tn)
        return
            
    r = generic(src, 'TEST', 'test ' + rand + ' ' + baddr + ' ' + daddr + ' ' + str(dport) + '\n')
    if r is None:   # connection error
        return
    log.info('MM:' + src + ' TEST ' + tn + ': ' + r.strip())
    
    if r.find("ERROR") >= 0:
        log.error('MM:' + src + ' ERROR: TEST ' + tn + ' TEST FAILED ON SOURCE ' + r.strip())
        return
    
    for _ in range(5):
        result = generic(xdst, 'RESULT', 'result ' + rand + '\n')
        tokens = result.split()
        # possible return codes are:
        # COMPLETE - transfer is done
        # FAILURE - transfer is complete but a fault occurred
        # PENDING - transfer is still in progress
        # UNKNOWN - this host has no record of this transfer (misdirected)
        if result.find('COMPLETE') >= 0:
            log.info('MM:' + xdst + ' TEST PASSED ' + tn + ' ' + rand + ' ' + tokens[3] + ' ' + tokens[4] + ' ' + tokens[5])
            return
        if result.find('PENDING') >= 0:
            log.info('MM:' + xdst + ' TEST TRANSFER STILL IN PROGRESS ' + tn + ' ' + rand)
            time.sleep(1)
            continue
        if result.find('FAILURE') >= 0:
            log.error('MM:' + xdst + ' TEST FAILED ' + tn + ' BAD RESULT (' + result + ')')
            return
        if result.find('UNKNOWN') >= 0:
            log.error('MM:' + xdst + ' TEST FAILED ' + tn + ' DATA NOT FOUND ON EXPECTED HOST (' + xdst + ') - checking all hosts')
            for h in sorted(hosts):
                p = generic(h, 'RESULT', 'result ' + rand + '\n')
                if p.find('COMPLETE') >= 0:
                    log.error('MM:' + h + ' TEST MISDIRECTED ' + tn + ' ' + rand + ' to ' + p.strip())
                    return
            log.error('MM:' + h + ' TEST LOST ' + tn + ' ' + rand)
            return
    log.error('MM:' + xdst + ' TEST FAILED ' + tn + ' ' + rand + ' PENDING TOO LONG')


# retrieve any pending or completed test results (does not consume result)

def pending (host):
    r = generic(host, 'RESULT', 'result\n')
    if r is not None and len(r) > 0:
        log.info('MM:' + host + ' PENDING: ' + r.strip())
    

def regress (rtest):
    global regressions

    try:
        r = regressions[rtest]
    except:
        log.error('MM:00 ERROR: REGRESSION TEST FAILED unknown or poorly specified cmd: ' + rtest)
        return
    log.info('MM:00 INFO: REGRESSION TEST: ' + rtest + ": " + r)
    for l in shlex.split(r):
        parse(l)
    
    
def listener (host):    
    l = config["hosts"][host]
    addr = l['bind']
    for p in l['ports']:
        r = generic(host, 'LISTENER', 'listener ' + addr + ' ' + str(p) + '\n')
        if r is not None and len(r) > 0:
            log.info('MM:' + host + ' LISTENER: ' + r.strip())
  
            
def show (args):
    print 'Hosts and Listening Interfaces:'
    for h in sorted(hosts):
        print h + ':'
        for i in sorted(hosts[h]['interfaces']):
            iv = hosts[h]['interfaces'][i]
            print '  ' + i + ': ' + iv.get('bind', '<MISSING BIND>') + ':' + str(iv.get('port', '<MISSING PORT>'))
    print
    print 'Tests: src -> dst with expected Listener:'
    for t in sorted(tests):
        tv = tests[t]
        print '  ' + t + ': ' + tv.get('src', '<SRC>') + \
            '(' + tv.get('baddr', '<BIND>') + ') -> ' + \
            tv.get('daddr', '<DADDR>') + ':' + \
            str(tv.get('dport', '<DPORT>')) + \
            '   exp: ' + tv.get('xdst', '<XDST>') + ':' + tv.get('xifc', '<XIFC>')
    print
    print 'Commands:'
    for c in sorted(commands):
        print '  ' + c + ': ' + commands[c]
    if len(args) != 1:
        print
        print 'Complete configuration:'
        print json.dumps(config, indent=4, sort_keys=True)
 
        
def terminate (args):
    log.info('MM:00 EXITING')
    os._exit(0)

        
def usage (args):
    for h in sorted(cmdfuncs):
        msg = cmdfuncs.get(h)[2]
        if msg is not None:
            print h + ':  ' + msg
    print
    print 'usual sequence is: dump, listener, test'

        
def base36(s):
    n = 0
    for c in string.lower(s):
        if c.isdigit():
            n = n * 36 + ord(c) - ord('0')
            continue
        if c.isalpha():
            n = n * 36 + ord(c) - ord('a') + 10
            continue
        n = n * 36 + 35  #treat everything else as a 'z'
    return n

        
if __name__ == "__main__":
    main(sys.argv)
