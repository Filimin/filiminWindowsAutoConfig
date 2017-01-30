"""
Filimin AutoConfig
Autoconfigure Filimin for Windows Machines
v0.1.2
John Harrison
"""

import autoConfigUi as ui
from PyQt4 import QtCore, QtGui
import sys, subprocess, time, tempfile, urllib, urllib2, os
import icons_rc
import traceback

secsForFiliminSSID = 30

#************************************************************************
# CLASS FOR CONTROLLER
#************************************************************************


class Worker(QtCore.QThread):
    showDialog = QtCore.pyqtSignal(object)
    exception = QtCore.pyqtSignal(object)
    success = QtCore.pyqtSignal(object)
    updateEventSlot = QtCore.pyqtSignal(object)
    retrySlot = QtCore.pyqtSignal(object)
    killSlot = QtCore.pyqtSignal(object)
    step = 0
    
    def __init__(self, parent = None):
        self.thread = QtCore.QThread.__init__(self, parent)
        # self.exiting = False # not sure what this line is for
        print "worker thread initializing"
        sys.excepthook = self.excepthook # FIXME
        self.owner = parent

    def run(self):
        self.initUi()
        self.retrySlot.connect(self.retry)
        self.giveIntroToUser(self.run,self.fail)
        print "worker thread running"
        self.dialogWindow = True
        while self.dialogWindow:
            time.sleep(1)
        credentials = self.getWiFiCredentials()
        print "credentials: "+credentials[0]+" "+credentials[1]
        ssid = self.getFiliminSSID()
        profile = self.createAndLoadProfile(ssid)
        confirmed = False
        tries = 1
        while not confirmed and tries < 3:
            print "Confirming: "+str(tries)
            self.connectToFilimin(ssid)
            confirmed = self.readAndWriteToFilimin(credentials, tries)
            tries += 1
        self.connectBackToWiFi(credentials, confirmed)
        self.finishUp(confirmed)
        # getattr(self, self.steps[self.step])(self.steps[self.step+1],
        #                                     self.steps[len(self.steps)-1])

    def __del__(self):
        print "worker thread dieing"

    def excepthook(self, excType, excValue, tracebackobj):
        """
        Global function to catch unhandled exceptions.

        @param excType exception type
        @param excValue exception value
        @param tracebackobj traceback object
        """
        notice = \
                 """Filimin Autoconfigure has encountered an unexpected error.\n"""\
                 """Please report the below information to support@filimin.com:\n\n"""
        msg = str(notice)+str(excType)+"\n"+str(excValue)+"\n"+str(traceback.format_tb(tracebackobj))
        self.exception.emit(msg) # if uncommented prevents fail signal?

    toHex = lambda self,x:"".join([hex(ord(c))[2:].zfill(2) for c in x])

    def fail(self, str):
        msg = "Autoconfiguration Error: "+str
        print msg
        self.updateEventSlot.emit({'state':'failure'})
        self.exception.emit(msg)
        while True:
            time.sleep(1)

    def retry(self):
        subprocess.Popen([os.path.abspath("autoConfig.exe")])
        self.killSlot.emit({})
        return
        
    def executeCmd(self, cmd):
        result = subprocess.check_output(cmd, universal_newlines=True, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        result = result.split('\n')
        return result

    def findInList(self, needle, haystack, start=0):
        cnt = 0
        for i in haystack:
            if needle in i and cnt >= start:
                return cnt
            cnt += 1
        return -1

    def initUi(self):
        self.updateEventSlot.emit({'step':0, 'state':'blank'})
        
    def giveIntroToUser(self,success,failure):
        self.showDialog.emit([success,failure])
        
    def getWiFiProfile(self):
        result = self.executeCmd(["netsh","wlan", "show", "interfaces"])
        if self.findInList('There is 1 interface', result) == -1:
            self.fail("This app does not support devices which more than one interface.")
        state = self.findInList('State', result)
        if state == -1:
            self.fail("Could not find state of WiFi interface. Is your WiFi on this device enabled?")
        connected = ("connected" in result[state])
        if connected != True:
            self.fail("WiFi Interface appears to not be connected. Connect this device to your WiFi and try again.")
        if self.findInList('SSID                   : Filimin_', result) != -1:
            self.fail("This device is connected to a Filimin. Connect to the your router (the Internet) instead and try again.")
        c = self.findInList('Channel', result)
        try:
            channel = result[c][result[c].index(':')+2:] # NEED TRY/CATCH HERE
            channel = int(channel)
        except:
            self.fail("Your Wi-Fi is not on or is not connected to the Internet. Turn on the Wi-Fi and confirm your Internet is working on this device. Then try again.")
        if channel > 14:
            self.fail("It appears you are connected to a 5Ghz channel. Filimins support only 2.4Ghz channels.\nIf possible, reconnect your device to a 2.4Ghz channel on your router and try again.")
        r = self.findInList('Authentication', result)
        authType = result[r][result[r].index(':')+2:]
        aTypes = ['WPA2-Personal', 'Open', 'WPA-Personal', 'WEP']
        match = False
        for aType in aTypes:
            if authType == aType:
                match = True
        if not match:
            self.fail("Authentication "+authType+" not supported by Filimin. Supported types: WPA2-Personal, Open, WPA-Personal, WEP")
        profile = self.findInList('Profile                :', result)
        if profile == -1:
            self.fail("Could not find profile")
        profileName = result[profile][result[profile].index(':')+2:-1]
        return profileName

    def getSSIDAndPw(self, profile):
        result = self.executeCmd(["netsh","wlan", "show", "profile", "name="+profile, "key=clear"])
        nameLine = self.findInList('SSID name', result)
        if nameLine == -1:
            self.fail("Could not find SSID in profile")
        ssid = result[nameLine][result[nameLine].index('"')+1:-1]
        keyLine = self.findInList('Security key', result)
        keyStatus = result[keyLine][result[keyLine].index(':')+2:]
        if keyStatus == "Absent":
            pw = ''
        else:
            pwLine = self.findInList('Key Content', result)
            if pwLine == -1:
                self.fail("Permissions Error: Cannot read Wi-Fi password. Please abort this app and re-run as an Administrator")
            else:
                pw = result[pwLine][result[pwLine].index(':')+2:]
        return [ssid, pw]
    
    def getWiFiCredentials(self):
        print "wifi credentials"
        self.updateEventSlot.emit({'step':1, 'state':'spinning'})
        time.sleep(3) # seems like if we try to see the Filimin too quickly after unplug/replug it's bad?
        profile = self.getWiFiProfile()
        print "Profile: "+profile
        result = self.getSSIDAndPw(profile)
        ssid = result[0]
        pw = result [1]
        result.append(profile)
        print "SSID: "+ssid
        print "PW: "+pw
        return result

    def getFiliminSSID(self):
        tries = 0
        while tries < secsForFiliminSSID:
            print ".",
            result = self.executeCmd(["netsh","wlan", "show", "networks"])
            line = self.findInList("Filimin",result)
            if line != -1:
                break
            tries += 1
            time.sleep(1)
        print
        if tries >= secsForFiliminSSID:
            self.fail("Filimin not found. Is it plugged in? Unplug and replug your Filimin and try again.")
        filiminSSID = result[line][result[line].index("Filimin"):]
        print "Filimin SSID: >>>"+filiminSSID+"<<<"
        return filiminSSID
    
    def createAndLoadProfile(self, ssid):
        self.updateEventSlot.emit({'step':2, 'state':'spinning'})
        write = True
        hex = self.toHex(ssid)
        if getattr( sys, 'frozen', False ):
            basePath = sys._MEIPASS+"/"
        else:
            basePath = ''
        print "basePath:" +basePath
        fTemplate = open(basePath+'template.xml', 'r')
        fOut = tempfile.NamedTemporaryFile(suffix=".xml",delete=False)
        print 'temp file: '+fOut.name
        for line in fTemplate:
            if '<SSIDConfig>' in line:
                write = False
                fOut.write('<SSIDConfig>\n<SSID>\n<hex>'+hex+'</hex>\n<name>'+ssid+'</name>\n</SSID>\n</SSIDConfig>\n')
            elif '<name>' in line and write == True:
                fOut.write("<name>"+ssid+"</name>\n")
            elif '</SSIDConfig>' in line:
                write = True
            else:
                if write:
                    fOut.write(line)
        fOut.close()
        fTemplate.close()
        self.executeCmd(["netsh","wlan", "add", "profile", "filename="+fOut.name])

    def connectToNetwork(self, targetssid, profile, errorMsg):
        tries = 0
        while tries < 5:
            tries += 1
            result = self.executeCmd(["netsh","wlan", "connect", "name="+profile])
            t2 = 0
            state = -1
            while t2 < secsForFiliminSSID:
                time.sleep(1)
                result = self.executeCmd(["netsh","wlan", "show", "interfaces"])
                state = self.findInList("State                  : connected",result)
                if state != -1:
                    break;
                t2 += 1
            if state == -1:
                self.fail("Wi-Fi interface never connected")
            ssidLine = self.findInList("SSID", result)
            ssid = result[ssidLine][result[ssidLine].index(':')+2:]
            print "connected to SSID >>>"+ssid+"<<<"
            if ssid == targetssid:
                break
            print "connected to wrong network. Trying again..."
            time.sleep(1)
        if (ssid != targetssid):
            self.fail(errorMsg)
            
    def connectToFilimin(self,filiminName):
        self.updateEventSlot.emit({'step':3, 'state':'spinning'})
        self.connectToNetwork(filiminName, filiminName, "Cannot connect to Filimin")

    def getValue(self, key, haystack):
        start = haystack.index(key)+len(key)
        start = haystack.index(':',start)+1
        if haystack[start] == ' ':
            start += 1
        try:
            result = haystack[start:haystack.index(',',start)]
        except:
            result = haystack[start:haystack.index('}',start)]
        return result
    
    def readAndWriteToFilimin(self, credentials, tries):
        self.updateEventSlot.emit({'step':4, 'state':'spinning'})
        name = credentials[0]
        pw = credentials[1]
        try:
            inData = urllib2.urlopen('http://192.168.4.1/sendDataFromFilimin')
            print "reading from Filimin"
            data = inData.read()
        except:
            return False
        print data
        dStart =  data.index('connectedToSSID')+20
        currentSSID = data[dStart:data.index('"',dStart)]
        print "Filimin Current SSID: "+currentSSID
        confirmed = False
        self.updateEventSlot.emit({'step':5, 'state':'spinning'})
        if currentSSID == name and tries > 1:
            print "Confirmed after try: "+str(tries)
            confirmed = True
        time.sleep(1)
        oldData = data
        data = {"startColor" : self.getValue("startColor",oldData),
                "endColor" : self.getValue("endColor",oldData),
                "limitColors" : self.getValue("limitColors",oldData),
                "timeOffset" : self.getValue("timeOffset",oldData),
                "silentTimeStart" : self.getValue("silentTimeStart",oldData),
                "silentTimeEnd" : self.getValue("silentTimeEnd",oldData),
                "silentTimeEnabled" : self.getValue("silentTimeEnabled",oldData),
                "fadeTime" : self.getValue("fadeTime",oldData),}

        # data = {}
        data['ssid'] = name
        data['pw'] = pw
        data = urllib.urlencode(data)
        print "writing to Filimin: "+ data
        try:
            req = urllib2.Request('http://192.168.4.1/receiveDataToFilimin', data)
            response = urllib2.urlopen(req, timeout=10)
            filiminResponse = response.read()
            print "response: "+filiminResponse
            if filiminResponse == '{ "saved" : true }':
                print "response confirmed!"
                return True
            return False
            return confirmed
        except:
            print "Error"
            return False
            return confirmed

    def connectBackToWiFi(self, credentials, confirmed):
        if confirmed:
            self.updateEventSlot.emit({'step':6, 'state':'spinning'})
        ssid= credentials[0]
        profile = credentials[2]
        self.connectToNetwork(ssid, profile, "Cannot connect back to Wi-Fi")
        
    def finishUp(self, confirmed):
        if confirmed:
            self.success.emit('Configuration was successful. Your Filimin will now restart to connect to your Wi-Fi\nAfter it successfully connects, you should see a celebratory rainbow before it goes dark. To confirm you are connected successfully, touch the shade with your entire hand after this. You should see it react to your touch by changing between solid colors.')
            self.updateEventSlot.emit({'step':6, 'state':'complete'})
        else:
            self.step = 5
            self.fail("Could not confirm settings from your Filimin. It may not have configured correctly. Perhaps try again?")
        print "job done"
        
#************************************************************************
# MAKE IT ALL HAPPEN
#************************************************************************

    
if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    MyApp = ui.MyWindow(child=Worker)
    sys.exit(app.exec_())

