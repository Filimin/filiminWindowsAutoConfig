"""
Filimin AutoConfig
Autoconfigure Filimin for Windows Machines
v1.0
John Harrison
"""

import autoConfigUi as ui
from PyQt4 import QtCore, QtGui
import sys, subprocess, time, tempfile, urllib, urllib2
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
    
    step = 0
    
    def __init__(self, parent = None):
        QtCore.QThread.__init__(self, parent)
        # self.exiting = False # not sure what this line is for
        print "worker thread initializing"
        sys.excepthook = self.excepthook # FIXME
        self.owner = parent
        
    def run(self):
        self.initUi()
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
            self.connectToFilimin(ssid)
            confirmed = self.readAndWriteToFilimin(credentials, tries)
            tries += 1
        self.connectBackToWiFi(credentials)
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
        self.exception.emit(msg)

    toHex = lambda self,x:"".join([hex(ord(c))[2:].zfill(2) for c in x])

    def fail(self, str):
        # FIXME: actually do something here
        msg = "Autoconfiguration Failure: "+str+"\n\nThis app will now exit."
        print msg
        self.updateEventSlot.emit({'state':'failure'})
        self.exception.emit(msg)
        while True:
            time.sleep(1)
        
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
            self.fail("Found more than one interface")
        state = self.findInList('State', result)
        if state == -1:
            self.fail("Could not find state of interface")
        connected = ("connected" in result[state])
        if connected != True:
            self.fail("Interface appears to not be connected")
        if self.findInList('SSID                   : Filimin_', result) != -1:
            self.fail("Connected to a Filimin. Connect to the your router (the Internet) instead")
        c = self.findInList('Channel', result)
        try:
            channel = result[c][result[c].index(':')+2:] # NEED TRY/CATCH HERE
            channel = int(channel)
        except:
            self.fail("Your Wi-Fi is not on or is not connected to the Internet.")
        if channel > 14:
            self.fail("It appears you are connected to a 5Ghz channel. Filimins support only 2.4Ghz channels.\nReconnect your device to a 2.4Ghz channel on your router and try again")
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
        pwLine = self.findInList('Key Content', result)
        if pwLine == -1:
            pw = ''
        else:
            #self.fail("Could not find password") # FIXME what is there is no pw?
            pw = result[pwLine][result[pwLine].index(':')+2:]
        return [ssid, pw]
    
    def getWiFiCredentials(self):
        print "wifi credentials"
        self.updateEventSlot.emit({'step':1, 'state':'spinning'})
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
            self.fail("Filimin not found")
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
        while tries < secsForFiliminSSID:
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
            print "Confirmed after 1st try: "+str(tries)
            confirmed = True
        time.sleep(1)
        '''
        data = {"startColor" : 0,
                "endColor" : 255,
                "limitColors" : "false",
                "timeOffset" : 82800,
                "silentTimeStart":0,
                "silentTimeEnd":0,
                "silentTimeEnabled":"false",
                "fadeTime":0}
        '''
        data = {}
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
                print "YAY!"
                return True
            return confirmed
        except:
            print "Error"
            return confirmed

    def connectBackToWiFi(self, credentials):
        self.updateEventSlot.emit({'step':6, 'state':'spinning'})
        ssid= credentials[0]
        profile = credentials[2]
        self.connectToNetwork(ssid, profile, "Cannot connect back to Wi-Fi")
        
    def finishUp(self, confirmed):
        self.updateEventSlot.emit({'step':6, 'state':'complete'})
        self.success.emit('Configuration was successful. Your Filimin will now connect to your Wi-Fi\nAfter you see the celebratory rainbow, touch your Filimin to let somebody know you love them. :-)')
        print "job done"
        
#************************************************************************
# MAKE IT ALL HAPPEN
#************************************************************************

    
if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    MyApp = ui.MyWindow(child=Worker)
    sys.exit(app.exec_())

