#!/usr/bin/env python

import threading
import time
import os
import usb
import math
import re
from beedriver import logger

"""
* Copyright (c) 2015 BEEVC - Electronic Systems This file is part of BEESOFT
* software: you can redistribute it and/or modify it under the terms of the GNU
* General Public License as published by the Free Software Foundation, either
* version 3 of the License, or (at your option) any later version. BEESOFT is
* distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
* without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
* PARTICULAR PURPOSE. See the GNU General Public License for more details. You
* should have received a copy of the GNU General Public License along with
* BEESOFT. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "BVC Electronic Systems"
__license__ = ""


class LogThread(threading.Thread):
    r"""
        LogThread Class

        This class provides the methods to debug and log printer actions


    """

    # *************************************************************************
    #                        __init__ Method
    # *************************************************************************
    def __init__(self, connection, logJob='TemperatureLog', frequency=1,logFileName='aaa.csv', samples=0, hideLog=True):
        r"""
        __init__ Method

        Initializes this class

        """

        super(LogThread, self).__init__()

        self.beeCon = connection
        self._logJog = logJob
        self._freq = frequency
        self._logFileName = './logs/' + logFileName
        self._samples = samples
        self._logFile = None
        self._hideLog = hideLog
        self._stopLog = False

        if not os.path.exists('logs'):
            os.makedirs('logs')

        return

    # *************************************************************************
    #                        run Method
    # *************************************************************************
    def run(self):

        super(LogThread, self).run()

        #########################
        #    Temperature Log
        #########################
        if self._logJog == 'TemperatureLog':
            self._logFile = open(self._logFileName,'w')
            #self._logFile.write("T,B\n")
            self._logFile.close()
            self._logFile = open(self._logFileName,"a")
            if self._samples > 0:
                self.finiteTemperatureLog()
            else:
                self.continuousTemperatureLog()
            self._logFile.close()
            self.beeCon.sendCmd("M300\n")
            self.beeCon.sendCmd("M300\n")

        #########################
        #    Print Log
        #########################
        elif self._logJog == 'PrintLog':
            self._logFile = open(self._logFileName,'w')
            #logFile.write("Time,Current T,Target T,PWM Output,kp,ki,kd,pterm,iterm,dterm,Block T,Block Vent,Blower,Z\n")
            self._logFile.close()
            self._logFile = open(self._logFileName,"a")
            self.printingLog()
            self._logFile.close()

        #########################
        #    Printer Status Log
        #########################
        elif self._logJog == 'StatusLog':
            self._logFile = open(self._logFileName,'w')
            #logFile.write("Time,Current T,Target T,PWM Output,kp,ki,kd,pterm,iterm,dterm,Block T,Block Vent,Blower,Z\n")
            self._logFile.close()
            self._logFile = open(self._logFileName,"a")
            if self._samples > 0:
                self.finiteStatusLog()
            else:
                self.continuousStatusLog()
            self._logFile.close()


        logger.info('Exiting log thread')

        return


    # *************************************************************************
    #                        stop Method
    # *************************************************************************
    def stop(self):

        self._stopLog = True

        logger.info('Cancelling log thread')

        return

    # *************************************************************************
    #                        show Method
    # *************************************************************************
    def show(self):

        self._hideLog = False

        return

    # *************************************************************************
    #                        hide Method
    # *************************************************************************
    def hide(self):

        self._hideLog = True

        return

    # *************************************************************************
    #                        finiteTemperatureLog Method
    # *************************************************************************
    def finiteTemperatureLog(self):


        logger.info("Starting loging temperatures {} samples to {} at {} records per second".format(self._samples,self._logFileName,self._freq))

        for i in range(0,self._samples):
            reply = self.beeCon.sendCmd("M105\n")
            parsedLine = self.parseTemperatureReply(reply)
            if parsedLine is not None:
                self._logFile.write(parsedLine)
                if not self._hideLog:
                    logger.info("{}/{} {}".format(i,self._samples,parsedLine))

            if self._stopLog:
                break
            time.sleep(self._freq)


        return

    # *************************************************************************
    #                        finiteStatusLog Method
    # *************************************************************************
    def finiteStatusLog(self):


        logger.info("Starting loging Status {} samples to {} at {} records per second".format(self._samples,self._logFileName,self._freq))

        for i in range(0,self._samples):
            reply = self.beeCon.sendCmd("M1029\n")
            parsedLine = self.parseLogReply(reply)
            if parsedLine is not None:
                self._logFile.write(parsedLine)
                if not self._hideLog:
                    logger.info("{}/{} {}".format(i,self._samples,parsedLine))

            if self._stopLog:
                break
            time.sleep(self._freq)


        return

    # *************************************************************************
    #                        continuousStatusLog Method
    # *************************************************************************
    def continuousStatusLog(self):


        logger.info("Starting loging Status to {} at {} records per second".format(self._logFileName,self._freq))

        i = 0
        while not self._stopLog:
            reply = self.beeCon.sendCmd("M1029\n")
            parsedLine = self.parseLogReply(reply)
            if parsedLine is not None:
                i = i + 1
                self._logFile.write(parsedLine)
                if not self._hideLog:
                    logger.info("{}: {}".format(i,parsedLine))

            time.sleep(self._freq)


        return

    # *************************************************************************
    #                        continuousTemperatureLog Method
    # *************************************************************************
    def continuousTemperatureLog(self):


        logger.info("Starting loging temperatures to {} at {} records per second".format(self._logFileName,self._freq))

        i = 0
        while not self._stopLog:
            reply = self.beeCon.sendCmd("M105\n")
            parsedLine = self.parseTemperatureReply(reply)
            if parsedLine is not None:
                i = i + 1
                self._logFile.write(parsedLine)
                if not self._hideLog:
                    logger.info("{}: {}".format(i,parsedLine))

            time.sleep(self._freq)


        return

    # *************************************************************************
    #                        parseTemperatureReply Method
    # *************************************************************************
    def parseTemperatureReply(self, replyLine):

        logLine = None
        #reply = reply.replace('\n','')
        if('\n' in replyLine):
            #replyLines = reply.split('ok Q:')

            re1='(T)'	# Any Single Character 1
            re2='.*?'	# Non-greedy match on filler
            re3='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 1
            re4='.*?'	# Non-greedy match on filler
            re5='(B)'	# Any Single Character 2
            re6='.*?'	# Non-greedy match on filler
            re7='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 2
            re8='.*?'	# Non-greedy match on filler
            re9='(R)'	# Any Single Character 3
            re10='.*?'	# Non-greedy match on filler
            re11='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 3

            #rg = re.compile(re1+re2+re3+re4+re5+re6+re7+re8+re9,re.IGNORECASE|re.DOTALL)
            rg = re.compile(re1+re2+re3+re4+re5+re6+re7+re8+re9+re10+re11,re.IGNORECASE|re.DOTALL)
            #m = rg.search(replyLines[0])
            m = rg.search(replyLine)
            if m:
                w1=m.group(1)
                float1=m.group(2)
                w2=m.group(3)
                float2=m.group(4)
                w3=m.group(5)
                float3=m.group(6)
                logLine = "{},{},{}\n".format(float1,float2,float3)

        return logLine

    # *************************************************************************
    #                        printingLog Method
    # *************************************************************************
    def printingLog(self):

        beeCmd = self.beeCon.getCommandIntf()

        while beeCmd.getStatus() is None:
            logger.info("Waiting for print to start")
            time.sleep(self._freq)

        logger.info("Starting loging temperatures during print to {} at {} records per second".format(self._logFileName,self._freq))

        self._stopLog = False

        elapsedTime = 0
        i = 0
        while not self._stopLog:
            st = beeCmd.getStatus()
            if st is not None:
                if 'SD_Print' not in st:
                    self._stopLog = True
            reply = beeCmd.sendCmd("M1029\n")

            parsedLine = self.parseLogReply(reply)
            if parsedLine is not None:
                i = i + 1
                self._logFile.write("{},{}".format(elapsedTime,parsedLine))
                if not self._hideLog:
                    logger.info("{}: {}".format(i,parsedLine))

            time.sleep(self._freq)
            elapsedTime = elapsedTime + self._freq



        return

    # *************************************************************************
    #                        parseLogReply Method
    # *************************************************************************
    def parseLogReply(self, replyLine):

        logLine = None

        if('\n' in replyLine):
            replyLines = replyLine.split('ok Q:')

            re1='((?:[a-z][a-z0-9_]*))'	# Variable Name 1
            re2='(.)'	# Any Single Character 1
            re3='.*?'	# Non-greedy match on filler
            re4='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 1
            re5='.*?'	# Non-greedy match on filler
            re6='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 2
            re7='.*?'	# Non-greedy match on filler
            re8='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 3
            re9='.*?'	# Non-greedy match on filler
            re10='((?:[a-z][a-z0-9_]*))'	# Variable Name 2
            re11='.*?'	# Non-greedy match on filler
            re12='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 4
            re13='.*?'	# Non-greedy match on filler
            re14='((?:[a-z][a-z0-9_]*))'	# Variable Name 3
            re15='.*?'	# Non-greedy match on filler
            re16='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 5
            re17='.*?'	# Non-greedy match on filler
            re18='((?:[a-z][a-z0-9_]*))'	# Variable Name 4
            re19='.*?'	# Non-greedy match on filler
            re20='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 6
            re21='.*?'	# Non-greedy match on filler
            re22='((?:[a-z][a-z0-9_]*))'	# Variable Name 5
            re23='.*?'	# Non-greedy match on filler
            re24='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 7
            re25='.*?'	# Non-greedy match on filler
            re26='((?:[a-z][a-z0-9_]*))'	# Variable Name 6
            re27='.*?'	# Non-greedy match on filler
            re28='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 8
            re29='.*?'	# Non-greedy match on filler
            re30='((?:[a-z][a-z0-9_]*))'	# Variable Name 7
            re31='.*?'	# Non-greedy match on filler
            re32='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 9
            re33='.*?'	# Non-greedy match on filler
            re34='((?:[a-z][a-z0-9_]*))'	# Variable Name 8
            re35='.*?'	# Non-greedy match on filler
            re36='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 10
            re37='.*?'	# Non-greedy match on filler
            re38='((?:[a-z][a-z0-9_]*))'	# Variable Name 9
            re39='.*?'	# Non-greedy match on filler
            re40='(\\d+)'	# Integer Number 1
            re41='.*?'	# Non-greedy match on filler
            re42='((?:[a-z][a-z0-9_]*))'	# Variable Name 10
            re43='.*?'	# Non-greedy match on filler
            re44='(\\d+)'	# Integer Number 2
            re45='.*?'	# Non-greedy match on filler
            re46='((?:[a-z][a-z0-9_]*))'	# Variable Name 11
            re47='.*?'	# Non-greedy match on filler
            re48='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 11

            rg = re.compile(re1+re2+re3+re4+re5+re6+re7+re8+re9+re10+re11+re12+re13+re14+re15+re16+re17+re18+re19+re20+re21+re22+re23+re24+re25+re26+re27+re28+re29+re30+re31+re32+re33+re34+re35+re36+re37+re38+re39+re40+re41+re42+re43+re44+re45+re46+re47+re48,re.IGNORECASE|re.DOTALL)

            m = rg.search(replyLines[0])
            #m = rg.search(reply)
            if m:
                var1=m.group(1)
                c1=m.group(2)
                float1=m.group(3)
                float2=m.group(4)
                float3=m.group(5)
                var2=m.group(6)
                float4=m.group(7)
                var3=m.group(8)
                float5=m.group(9)
                var4=m.group(10)
                float6=m.group(11)
                var5=m.group(12)
                float7=m.group(13)
                var6=m.group(14)
                float8=m.group(15)
                var7=m.group(16)
                float9=m.group(17)
                var8=m.group(18)
                float10=m.group(19)
                var9=m.group(20)
                int1=m.group(21)
                var10=m.group(22)
                int2=m.group(23)
                var11=m.group(24)
                float11=m.group(25)
                logLine = "{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(float1,float2,float3,float4,float5,float6,float7,float8,float9,float10,int1,int2,float11)

        return logLine