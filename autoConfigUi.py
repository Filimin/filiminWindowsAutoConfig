import sys, time, os
from PyQt4 import QtCore, QtGui
from autoConfigMainWindow import Ui_MainWindow
from introWindow import Ui_Dialog

TOTAL_STEPS = 6

#************************************************************************
# CLASS FOR GUI WINDOW
#************************************************************************
class MyDialog(QtGui.QDialog):
    def accept(self):
        print "accept called"
        self.hide()
        self.worker.dialogWindow=False

    def reject(self):
        print "reject called"
        self.hide()
        self.parent.leaveTheParty()
        
    def __init__(self, parent=None, worker=None):
        QtGui.QWidget.__init__(self, parent)
        self.worker = worker
        self.parent = parent
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setModal(True)
        self.worker.showDialog.connect(self.showIntroWindow)

    def showIntroWindow(self, result):
        self.accept = result[0]
        self.reject = result[1]
        self.show()

    def closeEvent(self, parameter):
        print "hello close "+str(parameter)
        self.hide()
        self.parent.leaveTheParty()

class MyMessageBox(QtGui.QMessageBox):
    def __init__(self, parent=None, worker=None):
        QtGui.QWidget.__init__(self, parent)
        self.worker = worker
        self.parent = parent
    
    def closeEvent(self, parameter):
        print "hello close "+str(parameter)
        self.parent.leaveTheParty()
    
class MyWindow(QtGui.QMainWindow):

    step = 0
    state = ''
    rotate = 0
    
    def __init__(self, parent=None, child=None):
        QtGui.QWidget.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # if you wish to use a timeout function, uncomment below:
        self.ctimer = QtCore.QTimer()
        self.ctimer.start(25) # timeout every 100 ms
        QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.UpdateDisplay)

        # if you wish to spin off independent thread for backend uncomment below:
        self.thread = child(self)
        self.myDialog = MyDialog(parent=self, worker=self.thread)
        self.thread.exception.connect(self.excepthook)
        self.thread.success.connect(self.sayGoodbye)
        self.thread.updateEventSlot.connect(self.updateEventUi)
        self.thread.killSlot.connect(self.leaveTheParty)
        '''
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Critical)

        msg.setText("This is a message box")
        msg.setInformativeText("This is additional information. asd asdf sadf asd fasdf as dfas f saf asdf asdf asf sadf as df asdf asdf as df asdf asd fas df asdf asdf asdf asd fas f asdf sdf sadf wsdf sadf ad fsdf sadf")
        msg.setWindowTitle("MessageBox demo")
        # msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QtGui.QMessageBox.Retry | QtGui.QMessageBox.Close)
        msg.buttonClicked.connect(self.testButtonClick)

        # retval = msg.exec_()
        msg.exec_()
        '''
        self.show()
        self.thread.start()

    def testButtonClick(self, msg):
        print "msg"
        print msg.text()
        
    def closeEvent(self, parent=None):
        # print "closing GUI window"
        pass

    def msgBox(self, icon, title, msg):
        # box = QtGui.QMessageBox()
        box = MyMessageBox(parent=self, worker=self.thread)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(str(msg))
        box.buttonClicked.connect(self.checkIfThePartyIsOver)        
        if title == "Error":
            box.setStandardButtons(QtGui.QMessageBox.Retry | QtGui.QMessageBox.Abort )
        else:
            box.setStandardButtons(QtGui.QMessageBox.Ok)
        retval = box.exec_()

    def excepthook(self, msg):
        self.msgBox(QtGui.QMessageBox.Critical, "Error", msg) 

    def sayGoodbye(self, msg):
        self.msgBox(QtGui.QMessageBox.Information, "Success", msg) 

    def checkIfThePartyIsOver(self, msg):
        if msg.text() != "Abort" and msg.text() != "OK":
            print msg.text()
            self.thread.retrySlot.emit(self)
        else:
            self.leaveTheParty()
            
    def leaveTheParty(self):
        self.deleteLater() # This ends the party

    def updateEventUi(self, updateInfo):
        if 'step' in updateInfo:
            self.step = updateInfo['step']
        print "step: "+str(self.step)
        self.state = updateInfo['state']
        if getattr( sys, 'frozen', False ):
            basePath = sys._MEIPASS+"/"
        else:
            basePath = ''
        print "basePath:" +basePath

        for i in range(self.step+1,TOTAL_STEPS+1):
            icon = getattr(self.ui,'step'+str(i)+'Icon')
            text = getattr(self.ui,'step'+str(i)+'Text')
            icon.setPixmap(QtGui.QPixmap(basePath+"resources/blank.png"))
            text.setStyleSheet("QWidget {color:#BBBBBB}")
        if self.step == 0:
            return
        self.rotate = 0
        icon = getattr(self.ui,'step'+str(self.step)+'Icon')
        text = getattr(self.ui,'step'+str(self.step)+'Text')        
        icon.setPixmap(QtGui.QPixmap(basePath+"resources/"+self.state+".png"))
        text.setStyleSheet("QWidget {color:#000000}")
        for i in range(1, self.step):
            icon = getattr(self.ui,'step'+str(i)+'Icon')
            text = getattr(self.ui,'step'+str(i)+'Text')
            icon.setPixmap(QtGui.QPixmap(basePath+"resources/complete.png"))
            text.setStyleSheet("QWidget {color:#000000}")
        print "update EventUI reporting in"
        
    def UpdateDisplay(self):
        # called by timeout function
        if (self.state != 'spinning'):
            return
        if getattr( sys, 'frozen', False ):
            basePath = sys._MEIPASS+"/"
        else:
            basePath = ''
        self.pixmap = QtGui.QPixmap(basePath+'resources/spinning.png')
        # diag = (self.pixmap.width()**2 + self.pixmap.height()**2)**0.5
        diag = 32
        self.pixmap = self.pixmap.transformed(QtGui.QTransform().rotate(self.rotate), QtCore.Qt.SmoothTransformation)
        self.rotate += 5
        icon = getattr(self.ui,'step'+str(self.step)+'Icon')
        icon.setMinimumSize(diag, diag)
        icon.setMaximumSize(diag, diag)
        icon.setAlignment(QtCore.Qt.AlignCenter)
        icon.setPixmap(self.pixmap)
        '''
        myFont.setPointSize(20)
        myFont.setBold(self.x % 10)
        self.ui.label.setFont(myFont)
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Foreground,QtCore.Qt.red)
        self.ui.label.setPalette(palette)
        '''
