#!/usr/bin/env python
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

import os
import sys
import time
from beedriver import connection
from beedriver import logThread
import logging
import re

# Logger configuration
logger = logging.getLogger('beeconsole')
logger.setLevel(logging.INFO)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# add the handlers to logger
logger.addHandler(ch)


class Console:

    r"""
    Bee Console - Terminal console for the BeeTheFirst 3D Printer

    Every new line inserted in the console is processed in 2 different categories:

    Printer commands:
        Single M & G code lines.

    Operation Commands:
        Commands to do specific operations, like load filament and transfer files.
        Operation commands always start with an "-"

        The following operation commands are implemented:

        * "-load" Load filament operation
        * "-unload" Unload filament operation
        * "-gcode LOCALFILE_PATH R2C2_FILENAME" Transfer gcode file to Printer.

                LOCALFILE_PATH -> filepath to file
                R2C2_FILENAME -> Name to be used when writing in printer memory (Optional)

        * "-flash <LOCALFILE_PATH> <Firmware string> Flash Firmware.

                LOCALFILE_PATH -> filepath to file
                Firmware string  -> Firmware string

        * "-exit" Closes console


    """
    beeConn = None
    beeCmd = None

    connected = False
    exit = False

    exitState = None

    mode = "None"

    logThread = None

    # *************************************************************************
    #                            Init Method
    # *************************************************************************
    def __init__(self, findAll = False):

        self.connected = False
        self.exit = False
        self.exitState = None

        nextPullTime = time.time() + 1

        logger.info("Waiting for printer connection...")

        while (not self.connected) and (not self.exit):

            t = time.time()

            if t > nextPullTime:

                self.beeConn = connection.Conn()
                # Connect to first Printers
                #findAll = True
                if findAll:
                    printerlist = self.beeConn.getPrinterList();
                    if len(printerlist) > 1:
                        print("Choose printer from list:")
                        i = 0
                        for printer in printerlist:
                            print("{}: Printer Name:{}      with serial number:{}\n".format(i,printer['Product'],printer['Serial Number']))
                            i = i + 1

                        selesctedPrinterIdx = raw_input(':')
                        if selesctedPrinterIdx.isdigit() and 0 <= int(selesctedPrinterIdx) < len(printerlist):
                            self.beeConn.connectToPrinter(printerlist[int(selesctedPrinterIdx)])
                    else:
                        self.beeConn.connectToFirstPrinter()
                else:
                    self.beeConn.connectToFirstPrinter()

                if self.beeConn.isConnected() is True:

                    self.beeCmd = self.beeConn.getCommandIntf()

                    self.mode = self.beeCmd.getPrinterMode()

                    # USB Buffer need cleaning
                    if self.mode is None:
                        logger.info('Printer not responding... cleaning buffer\n')
                        self.beeCmd.cleanBuffer()

                        self.beeConn.close()
                        self.beeConn = None
                        # return None

                    # Printer ready
                    else:
                        self.connected = True

                nextPullTime = time.time() + 1

        logger.info('Printer started in %s mode\n' % self.mode)

        status = self.beeCmd.getStatus()
        if status is not None:
            if 'Shutdown' in status:
                logger.info('Printer recovering from shutdown. Choose action:\n')
                logger.info('0: Resume print\n')
                logger.info('1: Cancel print\n')
                logger.info('2: Continue\n')
                i = int(raw_input(">:"))
                if i == 0:
                    self.beeCmd.resumePrint()
                elif i == 1:
                    self.beeCmd.clearShutdownFlag()

        return

    # *************************************************************************
    #                            listPrinters Method
    # *************************************************************************
    @staticmethod
    def listPrinters(printers):

        for i in range(len(printers)):
            logger.info('%s: %s with serial number: %s',str(i),printers[i]['Product'],str(printers[i]['Serial Number']))

        return

    # *************************************************************************
    #                           END Console Interface
    # *************************************************************************


done = False

newestFirmwareVersion = 'MSFT-BEETHEFIRST-10.4.0'
fwFile = 'MSFT-BEETHEFIRST-Firmware-10.4.0.BIN'


# *************************************************************************
#                            startLog Method
# *************************************************************************
def startLog(var,console):

    freq = 1
    samples = 0

    logType = raw_input('Choose log type:\n0: Temperature Log\n1: Printing Log\n2: Printer Debug Log\n')
    logTypeInt = None
    try:
        logTypeInt = int(logType)
        if logTypeInt < 0 or logTypeInt > 2:
            logTypeInt = None
    except:
        logTypeInt = None

    if logTypeInt is None:
        logger.info('Invalid Log Type Input')
        return

    logPrefix = ''
    if logTypeInt == 0:
        logPrefix = 'TemperatureLog'
    elif logTypeInt == 1:
        logPrefix = 'PrintLog'
    elif logTypeInt == 2:
        logPrefix = 'StatusLog'

    logFileName = '{}_{}_{}.csv'.format(logPrefix,time.strftime("%d_%m_%y"),time.strftime("%H_%M_%S"))

    cInput = raw_input("Enter Log File Name [{}]".format(logFileName))
    if cInput != '':
        logFileName = cInput

    cInput = raw_input("Enter Frequency [{}]:".format(freq))
    freqInput = None
    if cInput == '':
        freq = 1.0
    else:
        try:
            freq = float(cInput)
        except:
            logger.info('Invalid Frequency Input')
            return

    samples = 0
    if logTypeInt != 1:
        cInput = raw_input("Enter Number of Samples [0: continuous sampling]")
        try:
            if cInput == '':
                cInput = '0'
            samplesInt = int(cInput)
            if samplesInt < 0:
                samples = None
            else:
                samples = samplesInt
        except:
            samples = None

        if samples is None:
            logger.info('Invalid Number of Samples Number')
            return

        if cInput == '':
            samples

    cInput = raw_input("Hide log output [Y/n]")
    hideLog = True
    if cInput != '':
        if cInput.lower() == 'n':
            hideLog = False

    if logTypeInt == 0:
        console.logThread = logThread.LogThread(console.beeConn,'TemperatureLog',freq,logFileName,samples,hideLog)
        console.logThread.start()
    elif logTypeInt == 1:
        console.logThread = logThread.LogThread(console.beeConn,'PrintLog',freq,logFileName,hideLog)
        console.logThread.start()
    elif logTypeInt == 2:
        console.logThread = logThread.LogThread(console.beeConn,'StatusLog',freq,logFileName,samples,hideLog)
        console.logThread.start()

    print(cInput)


# *************************************************************************
#                            restart_program Method
# *************************************************************************
def restart_program():
    python = sys.executable
    os.execl(python, python, * sys.argv)


# *************************************************************************
#                            main Method
# *************************************************************************
def main(findAll = False):
    finished = False

    console = Console(findAll)

    if console.exit:
        if console.exitState == "restart":
            try:
                console.beeConn.close()
            except Exception as ex:
                logger.error("Error closing connection: %s", str(ex))

            console = None
            restart_program()

    while finished is False:
        var = raw_input(">:")
        # print(var)

        if not var:
            continue

        if "-exit" in var.lower():
            console.beeConn.close()
            console = None
            finished = True

        elif "mode" in var.lower():
            logger.info(console.mode)

        elif "-gcode" in var.lower():
            logger.info("Transfering GCode")
            args = var.split(" ")
            if len(args) > 2:
                console.beeCmd.transferSDFile(args[1],args[2])
            else:
                console.beeCmd.transferSDFile(args[1])
            #while console.beeCmd.getTransferCompletionState() is not None:
            #    time.sleep(0.5)

        elif "-load" in var.lower():
            logger.info("Loading filament")
            console.beeCmd.load()

        elif "-unload" in var.lower():
            logger.info("Unloading filament")
            console.beeCmd.unload()

        elif "-flash" in var.lower():
            logger.info("Flashing Firmware")
            args = var.split(" ")
            if len(args) > 2:
                console.beeCmd.flashFirmware(args[1], args[2])
            else:
                console.beeCmd.flashFirmware(args[1])

        elif "-print" in var.lower():
            args = var.split(" ")
            console.beeCmd.printFile(args[1],200)
        elif "-repeat" in var.lower():
            console.beeCmd.repeatLastPrint()
        elif "-temp" in var.lower():
            logger.info(console.beeCmd.getNozzleTemperature())

        elif "-cancel" in var.lower():
            console.beeCmd.cancelTransfer()
        elif "-status" in var.lower():
            logger.info(console.beeCmd.getTransferCompletionState())
        elif "-getcode" in var.lower():
            logger.info(console.beeCmd.getFilamentString())
        elif "-move" in var.lower():
            console.beeCmd.move(x=10,y=10,z=-10)

        elif "-log" in var.lower():

            startLog(var,console)

        elif "-stoplog" in var.lower():
            console.logThread.stop()

        elif "-hidelog" in var.lower():
            console.logThread.hide()

        elif "-showlog" in var.lower():
            console.logThread.show()

        elif "-setnozzle" in var.lower():

            splits = var.split(" ")
            nozzleSize = int(splits[1])

            logger.info("Defining new nozzle size: %i",nozzleSize)
            console.beeCmd.setNozzleSize(nozzleSize)

        elif "-setfil" in var.lower():

            splits = var.split(" ")
            fil = float(splits[1])

            logger.info("Defining filament in Spool: %f", fil)
            console.beeCmd.setFilamentInSpool(fil)

        elif "-getfil" in var.lower():

            logger.info("Filament in Spool: %f", console.beeCmd.getFilamentInSpool())

        elif "-pause" in var.lower():

            console.beeCmd.pausePrint()

        elif "-resume" in var.lower():

            console.beeCmd.resumePrint()

        elif "-sdown" in var.lower():

            console.beeCmd.enterShutdown()

        elif "-getnozzle" in var.lower():

            nozzleSize = console.beeCmd.getNozzleSize()
            logger.info("Current nozzle size: %i",nozzleSize)

        elif "-read" in var.lower():

            if not os.path.exists('reads'):
                os.makedirs('reads')

            args = var.split(" ")

            local_file = "./reads/local.gcode"
            if len(args) > 2:
                local_file = "./reads/" + str(args[2])

            printerFile = str(args[1])

            lFile = open(local_file,'w')

            done = False
            reply = ""

            reply = console.beeCmd.sendCmd("M21\n")
            reply = console.beeCmd.sendCmd("M23 {}\n".format(printerFile))
            reply = console.beeCmd.sendCmd("M34\n")

            start = time.time()
            nextPull = start + 1000
            lFile.write(reply)
            while not done:
                reply = ""
                tries = 5
                while reply == "" and not done:
                    tries -= 1
                    reply = console.beeConn.read()
                    time.sleep(0.005)
                    if tries < 0:
                        done = True

                lFile.write(reply)
            lFile.close()



        elif "-verify" in var.lower():
            logger.info("Newest Printer Firmware Available: %s", newestFirmwareVersion)
            currentVersionResp = console.beeCmd.sendCmd('M115', printReply=False)       # Ask Printer Firmware Version

            if newestFirmwareVersion in currentVersionResp:
                logger.info("Printer is already running the latest Firmware")
            else:
                printerModeResp = console.sendCmd('M116', printReply=False)      # Ask Printer Bootloader Version
                if 'Bad M-code' in printerModeResp:                             # Firmware Does not reply to M116 command, Bad M-Code Error
                    logger.info("Printer in Firmware, restarting your Printer to Bootloader")
                    console.beeCmd.sendCmd('M609', printReply=False)                    # Send Restart Command to Firmware
                    time.sleep(2)                                               # Small delay to make sure the board resets and establishes connection
                    # After Reset we must close existing connections and reconnect to the new device
                    while True:
                        try:
                            console.beeConn.close()          # close old connection
                            console = None
                            console = Console()     # search for printer and connect to the first
                            if console.connected is True:   # if connection is established proceed
                                break
                        except:
                            pass

                else:
                    logger.info("Printer is in Bootloader mode")

                console.beeCmd.flashFirmware(fwFile)         # Flash New Firmware
                #newFwCmd = 'M114 A' + newestFirmwareVersion  # prepare command string to set Firmware String
                #console.beeCmd.sendCmd(newFwCmd, printReply=False)  # Record New FW String in Bootloader
            # console.FlashFirmware(var)
        else:
            if "m630" in var.lower():
                console.beeCmd.goToFirmware()
                if 'Shutdown' in console.beeCmd.getStatus():
                    logger.info('Printer recovering from shutdown. Choose action:\n')
                    logger.info('0: Resume print\n')
                    logger.info('1: Cancel print\n')
                    logger.info('2: Continue\n')
                    i = int(raw_input(">:"))
                    if i == 0:
                        console.beeCmd.resumePrint()
                    elif i == 1:
                        console.beeCmd.clearShutdownFlag()
            elif "m609" in var.lower():
                console.beeCmd.goToBootloader()
            elif "m600" in var.lower():
                reply = console.beeCmd.sendCmd(var)
                while '\nok' not in reply:
                    reply += console.beeCmd.sendCmd('')
                logger.info(reply)

            else:
                logger.info(console.beeCmd.sendCmd(var))


if __name__ == "__main__":

    findAll = False

    for arg in sys.argv:
        re1 = '(findall)'  # Word 1
        re2 = '.*?'	 # Non-greedy match on filler
        re3 = '(true)'  # Variable Name 1
        rg = re.compile(re1+re2+re3, re.IGNORECASE | re.DOTALL)
        m = rg.search(arg.lower())
        if m:
            word1 = m.group(1)
            var1 = m.group(2)
            if word1 == "findall" and var1 == "true":
                findAll = True
                print("Search all printers enabled\n")

    main(findAll)
