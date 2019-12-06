#######################################################################################################
## G Taylor Feb 2019
##
## Self contained GUI to cool down a Chase cryogenics fridge mounted in a Giff-McMahon cryocooler to <1k
##
## Implemented on a raspberry pi for portability with the fridge
##
## Required Libraries:
## -hardware lib written by R Heath, bundled with this
## -PyQt5
## -PyVisa
##
########################################################################################################

####################
# Imports
import sys
from hardware import SIM900
from visa import *
from PyQt5 import QtGui, QtCore, QtWidgets
import csv
import time
####################

####################
# Main Body
class MainWindow(QtWidgets.QMainWindow): #Master object
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowIcon(QtGui.QIcon('snow.ico'))
        self.central_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central_widget)
        self.rm = ResourceManager()
        dev_setup_widget = DevSetup(self)
        self.central_widget.addWidget(dev_setup_widget)
        #Below are editable in the settings menu
        #SIM900 Slots
        self.ACBridgeSlot='5'
        self.ThermSlot1='8'
        #For logging
        self.log_file = "temp_log.txt"
        self.logging = False
        #Thresholds to tinker with
        self.CDStage1_ThHold = 4.2
        self.CDStage1_Pump_lower_temp = 45.0
        #timer if desired
        self.timer_on='hh:mm:ss'
        self.timer = False

        #Master counters and things
        self.current_pump_temp=''
        self.current_head_temp=''
        self.head_repeat_temps=0

        #Add menubar
        mainMenu=self.menuBar()
        settingsMenu=mainMenu.addMenu('Settings')
        settingsButton=QtWidgets.QAction('Change Settings', self)
        settingsButton.triggered.connect(self.change_settings)
        settingsMenu.addAction(settingsButton)

    def confirm_devs(self, Keithley_add, SIM900_add): #Confirms the device choices and opens the devices for use under the Master object, then switches views to the cooldown view
        self.Keithley = self.rm.open_resource(Keithley_add)
        self.Keithley.write("SYSTEM:REMOTE") #needed to work on pi/linux 
        self.SIM900 = SIM900(SIM900_add)
        cooldown_widget = Cooldown(self)
        self.central_widget.addWidget(cooldown_widget)
        self.central_widget.setCurrentWidget(cooldown_widget)

    def change_settings(self):
        self.sett=SettingsPage()
        self.sett.show()

class SettingsPage(QtWidgets.QWidget): #Settings page accessed from the menubar. Can configure thresholds and enable logging
    def __init__(self, parent=None):
        super(SettingsPage, self).__init__(parent)
        self.setGeometry(50, 50, 250, 200)
        self.setWindowTitle('Configure Settings')
        self.setWindowIcon(QtGui.QIcon('snow.ico'))
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)

        self.CDStage1_ThHold_lbl=QtWidgets.QLabel(self, text='Set threshold for cold head to reach before stage 2:')
        self.CDStage1_ThHold_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.CDStage1_ThHold_lbl, 0,0)
        self.CDStage1_ThHold_entry=QtWidgets.QLineEdit(self)
        self.CDStage1_ThHold_entry.setText(str(Master.CDStage1_ThHold))
        self.grid.addWidget(self.CDStage1_ThHold_entry, 0,1)

        self.CDStage1_Pump_lower_temp_lbl=QtWidgets.QLabel(self, text='Set lower bound for pump temp before Stage 2:')
        self.CDStage1_Pump_lower_temp_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.CDStage1_Pump_lower_temp_lbl, 1,0)
        self.CDStage1_Pump_lower_temp_entry=QtWidgets.QLineEdit(self)
        self.CDStage1_Pump_lower_temp_entry.setText(str(Master.CDStage1_Pump_lower_temp))
        self.grid.addWidget(self.CDStage1_Pump_lower_temp_entry, 1,1)

        self.logging_choice=QtWidgets.QCheckBox(self, text='Enable logging of temperatures?')
        self.grid.addWidget(self.logging_choice, 2,0)

        self.logging_file_lbl=QtWidgets.QLabel(self, text='Specify log file path:')
        self.logging_file_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.logging_file_lbl, 3,0)
        self.logging_file_entry=QtWidgets.QLineEdit(self)
        self.logging_file_entry.setText(str(Master.log_file))
        self.grid.addWidget(self.logging_file_entry, 3,1)

        self.timer_choice=QtWidgets.QCheckBox(self, text='Schedule cooldown?')
        self.grid.addWidget(self.timer_choice, 4,0)
        self.timer_on_lbl=QtWidgets.QLabel(self, text='Specify time in format hh:mm:ss:')
        self.timer_on_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.timer_on_lbl, 5,0)
        self.timer_on_entry=QtWidgets.QLineEdit(self)
        self.timer_on_entry.setText(str(Master.timer_on))
        self.grid.addWidget(self.timer_on_entry, 5,1)

        conf_butt = QtWidgets.QPushButton('Confirm', self)
        conf_butt.clicked.connect(lambda: self.confirm_and_close())
        self.grid.addWidget(conf_butt, 6,1)


    def confirm_and_close(self): #Confirms setting selections, updates master and closes the window
        Master.CDStage1_ThHold = float(self.CDStage1_ThHold_entry.text())
        Master.CDStage1_Pump_lower_temp = float(self.CDStage1_Pump_lower_temp_entry.text())
        if self.logging_choice.isChecked() == True:
            Master.logging = True
            Master.log_file = str(self.logging_file_entry.text())
        if self.timer_choice.isChecked() == True:
            Master.timer = True
            Master.timer_on = str(self.timer_on_entry.text())
        else:
            pass
        self.destroy()

class DevSetup(QtWidgets.QWidget): #Launch page where devices are defined from available list
    def __init__(self, parent=None):
        super(DevSetup, self).__init__(parent)
        self.get_devices(parent)
        self.parent().setGeometry(50, 50, 250, 100)
        self.parent().setWindowTitle('Device setup')
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)

        self.Keithley_lbl=QtWidgets.QLabel(self, text='Keithley source:')
        self.grid.addWidget(self.Keithley_lbl, 0,0)
        self.Keithley_opt=QtWidgets.QComboBox(self)
        self.populate_combo_box(self.Keithley_opt, self.dev_list)
        self.grid.addWidget(self.Keithley_opt, 0,1)
        
        self.SIM_lbl=QtWidgets.QLabel(self, text='SIM900:')
        self.grid.addWidget(self.SIM_lbl, 1,0)
        self.SIM_opt=QtWidgets.QComboBox(self)
        self.populate_combo_box(self.SIM_opt, self.dev_list)
        self.grid.addWidget(self.SIM_opt, 1,1)

        self.confirm_butt=QtWidgets.QPushButton('Confirm devices', self)
        self.confirm_butt.clicked.connect(lambda: self.conf_devs(parent))
        self.grid.addWidget(self.confirm_butt, 2,1)

    def get_devices(self, parent): #Gets available resources from the resource manager
        self.dev_list = parent.rm.list_resources() 

    def populate_combo_box(self, widget, list): #Helper function to populate a combobox
        for i in list:
            widget.addItem(i)

    def conf_devs(self, parent):#Checks for existance of devices
        if self.Keithley_opt.currentText() == '':
            self.msg = QtWidgets.QMessageBox()
            self.msg.setIcon(QtWidgets.QMessageBox.Warning)
            self.msg.setText("No fridge power source chosen!")
            self.msg.setWindowTitle("Error")
            self.msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            self.msg.show()
        elif self.SIM_opt.currentText() == '':
            self.msg = QtWidgets.QMessageBox()
            self.msg.setIcon(QtWidgets.QMessageBox.Warning)
            self.msg.setText("No SIM900 chosen!")
            self.msg.setWindowTitle("Error")
            self.msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            self.msg.show() 
        else:
            Keithley_add = self.Keithley_opt.currentText()
            SIM900_add = self.SIM_opt.currentText()
            parent.confirm_devs(Keithley_add, SIM900_add)


class Cooldown(QtWidgets.QWidget): #Cooldown page
    def __init__(self, parent=None):
        super(Cooldown, self).__init__(parent)
        self.parent().setGeometry(50, 50, 350, 200)
        self.parent().setWindowTitle('Cooldown')
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)
        self.Stage1 = False
        self.Stage2 = False

        ###Temperatures###

        self.temp_lbl=QtWidgets.QLabel(self, text='TEMPERATURES')
        self.temp_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.temp_lbl, 0,2,1,2)

        self.cold_head_lbl=QtWidgets.QLabel(self, text='Cold head:')
        self.grid.addWidget(self.cold_head_lbl, 1,2)
        self.cold_head_temp = QtWidgets.QLabel(self, text='0')
        self.cold_head_temp.setFrameShape(QtWidgets.QFrame.Panel)
        self.cold_head_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.cold_head_temp, 1,3)

        self.FB_lbl=QtWidgets.QLabel(self, text='Film burner:')
        self.grid.addWidget(self.FB_lbl, 2,2)
        self.FB_temp = QtWidgets.QLabel(self, text='0')
        self.FB_temp.setFrameShape(QtWidgets.QFrame.Panel)
        self.FB_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.FB_temp, 2,3)

        self.MP_lbl=QtWidgets.QLabel(self, text='Mainplate:')
        self.grid.addWidget(self.MP_lbl, 3,2)
        self.MP_temp = QtWidgets.QLabel(self, text='0')
        self.MP_temp.setFrameShape(QtWidgets.QFrame.Panel)
        self.MP_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.MP_temp, 3,3)

        self.He_pump_lbl=QtWidgets.QLabel(self, text='He pump:')
        self.grid.addWidget(self.He_pump_lbl, 4,2)
        self.He_pump_temp = QtWidgets.QLabel(self, text='0')
        self.He_pump_temp.setFrameShape(QtWidgets.QFrame.Panel)
        self.He_pump_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.He_pump_temp, 4,3)

        self.Heat_sw_lbl=QtWidgets.QLabel(self, text='Heat switch:')
        self.grid.addWidget(self.Heat_sw_lbl, 5,2)
        self.Heat_sw_temp = QtWidgets.QLabel(self, text='0')
        self.Heat_sw_temp.setFrameShape(QtWidgets.QFrame.Panel)
        self.Heat_sw_temp.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.Heat_sw_temp, 5,3)

        ###CONTROLS###

        self.ctrl_lbl=QtWidgets.QLabel(self, text='CONTROL')
        self.ctrl_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.ctrl_lbl, 0,0,1,2)

        self.start_butt=QtWidgets.QPushButton('Start cooldown', self)
        self.start_butt.clicked.connect(lambda: self.begin_cooldown())
        self.grid.addWidget(self.start_butt, 1,0,1,2)

        self.stop_butt=QtWidgets.QPushButton('Stop cooldown', self)
        self.stop_butt.setEnabled(False)
        self.stop_butt.clicked.connect(self.stop_cooldown)
        self.grid.addWidget(self.stop_butt, 2,0,1,2)

        self.start_stage2_butt=QtWidgets.QPushButton('Jump to stage 2', self)
        self.start_stage2_butt.clicked.connect(lambda: self.jump_to_stage_2())
        self.grid.addWidget(self.start_stage2_butt, 3,0,1,2)


        ###MONITORING###

        self.mon_lbl=QtWidgets.QLabel(self, text='MONITOR')
        self.mon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.grid.addWidget(self.mon_lbl, 4,0,1,2)

        self.stage_lbl=QtWidgets.QLabel(self, text='Stage:')
        self.grid.addWidget(self.stage_lbl, 5,0)
        self.stage_val=QtWidgets.QLabel(self, text='0')
        self.stage_val.setFrameShape(QtWidgets.QFrame.Panel)
        self.stage_val.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.stage_val, 5,1)

        self.el_time_lbl=QtWidgets.QLabel(self, text='Elapsed Time (hrs):')        
        self.grid.addWidget(self.el_time_lbl, 6,0)
        self.el_time=QtWidgets.QLabel(self, text='0')
        self.el_time.setFrameShape(QtWidgets.QFrame.Panel)
        self.el_time.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.grid.addWidget(self.el_time, 6,1)

    def begin_cooldown(self): #Kicks off temperature monitoring and 
        if Master.timer == True:
            if Master.timer_on == 'hh:mm:ss':
                self.msg = QtWidgets.QMessageBox()
                self.msg.setIcon(QtWidgets.QMessageBox.Warning)
                self.msg.setText("Invalid time entered in settings, no timer set!")
                self.msg.setWindowTitle("Error")
                self.msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
                self.msg.show()
                Master.timer = False
                self.begin_cooldown() 
            else:
                time_now=time.ctime()[11:19]
                time_now_s=(int(time_now[0:2])*3600)+(int(time_now[3:5])*60)+(int(time_now[6:8]))
                time_turn_on_s = (int(Master.timer_on[0:2])*3600)+(int(Master.timer_on[3:5])*60)+(int(Master.timer_on[6:8]))
                if time_turn_on_s < time_now:
                    wait_time=(86400-time_now)+time_turn_on_s #86400=seconds in day
                else:
                    wait_time=time_turn_on_s-time_now_s
                Master.timer = False
                QtCore.QTimer.singleShot((wait_time*1e3), self.begin_cooldown)        
        else:
            self.timer = QtCore.QTime()
            self.timer.start()
            if Master.logging == True:
                with open(self.log_file, 'a') as logging_file:
                    writer_log = csv.writer(logging_file)
                    writer_log.writerow(['timestamp(s)', 'c_head_temp(K)', 'film_burner_temp(K)', 'mainplate_temp(K)', 'he_pump_temp(K)', 'heat_sw_temp(K)'])
            #ensure VSources off
            Master.Keithley.write("INST:NSEL 1")
            Master.Keithley.write('CHAN:OUTP OFF')
            Master.Keithley.write("INST:NSEL 2")
            Master.Keithley.write('CHAN:OUTP OFF')
            #start temp monitors
            self.Temp_thread = TempThread()
            self.Temp_thread.update_GUI_sig.connect(self.update_GUI)
            self.Temp_thread.finished.connect(self.done)
            self.Temp_thread.start()
            self.stop_butt.setEnabled(True)
            self.start_butt.setEnabled(False)

    def stop_cooldown(self): #Stops the cooldown - disables all VSources and resets GUI
        prompt=QtWidgets.QMessageBox.question(self, 'Stop!', 'Are you sure you want to stop?', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if prompt == QtWidgets.QMessageBox.Yes:
            self.Temp_thread.terminate() #kill the threads
            try:
                self.CooldownThreadStage1.terminate()
            except AttributeError:
                pass
            try:
                self.CooldownThreadStage2.terminate()
            except AttributeError:
                pass    
            #Turn all voltage sources off
            Master.Keithley.write("INST:NSEL 1")
            Master.Keithley.write("VOLT 0")
            Master.Keithley.write('CHAN:OUTP OFF')
            Master.Keithley.write("INST:NSEL 2")
            Master.Keithley.write("VOLT 0")
            Master.Keithley.write('CHAN:OUTP OFF')
            self.Stage1 = False
            self.Stage2 = False
            self.stage_val.setText('0')
            self.stop_butt.setEnabled(False)
            self.start_butt.setEnabled(True)
        else:
            pass

    def update_GUI(self, temp_list): #Updates the GUI with temperatures and will initiate the stages as they are needed
        timestamp=self.timer.elapsed()
        self.el_time.setText(str(round(timestamp/3600000,3)))
        if Master.logging == True:
            with open(Master.log_file, 'a') as logging_file:
                writer_log = csv.writer(logging_file)
                log_entry=[str(timestamp)]+temp_list
                writer_log.writerow(log_entry)
        #This section recalibrates the SIM921 gain settings if the amp gets overloaded.
        if temp_list[0] == Master.current_head_temp:
            Master.head_repeat_temps += 1
        else:
            Master.current_head_temp = temp_list[0]
            Master.head_repeat_temps=0
        if Master.head_repeat_temps > 5:
            Master.SIM900.write(Master.ACBridgeSlot, 'AGAI ON')
            Master.head_repeat_temps = 0
        #Updates the GUI with the temperatures
        self.cold_head_temp.setText(temp_list[0])
        self.FB_temp.setText(temp_list[1])
        self.MP_temp.setText(temp_list[2])
        self.He_pump_temp.setText(temp_list[3])
        self.Heat_sw_temp.setText(temp_list[4])
        #master pump temp for cooldown thread.
        Master.current_pump_temp=temp_list[3]

        if self.Stage1 == False and self.Stage2 == False:
            #if float(self.He_pump_temp.text()) < 10.0:
            self.CooldownThreadStage1 = CooldownThreadStage1()
            self.CooldownThreadStage1.start()
            self.Stage1 = True
            self.stage_val.setText('1')

        if self.Stage1 == True:
            if float(self.He_pump_temp.text()) > Master.CDStage1_Pump_lower_temp and float(self.cold_head_temp.text()) < Master.CDStage1_ThHold:
                self.CooldownThreadStage1.terminate()
                Master.Keithley.write("INST:NSEL 1")
                Master.Keithley.write("VOLT 0")
                Master.Keithley.write('CHAN:OUTP OFF')
                self.Stage1 = False
                self.CooldownThreadStage2 = CooldownThreadStage2()
                self.CooldownThreadStage2.start()
                self.Stage2 = True
                self.stage_val.setText('2')
    
    def jump_to_stage_2(self): #For jumping to Stage2 before the head has cooled below the threshold
        prompt=QtWidgets.QMessageBox.question(self, 'Stop!', 'Are you sure you want to jump to stage 2? Hold time will be increased if the head is allowed to cool properly.', QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if prompt == QtWidgets.QMessageBox.Yes:
            self.Stage1 = False
            self.Stage2=True
            self.CooldownThreadStage1.terminate()
            Master.Keithley.write("INST:NSEL 1")
            Master.Keithley.write("VOLT 0")
            Master.Keithley.write('CHAN:OUTP OFF')
            self.CooldownThreadStage2 = CooldownThreadStage2()
            self.CooldownThreadStage2.start()
            self.stage_val.setText('2')
        else:
            pass

    def done(self):
        self.stop_butt.setEnabled(False)
        self.start_butt.setEnabled(True)


class TempThread(QtCore.QThread): #Read the thermometers and returns the data to the GUI
    #signals
    update_GUI_sig = QtCore.pyqtSignal(list) #self?

    def __init__(self, parent=None):
        super(TempThread, self).__init__(parent)

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            #read thermometers
            #punt data back to GUI
            c_head_temp = Master.SIM900.ask(Master.ACBridgeSlot, 'TVAL?') #Cold Head temp
            film_burner_temp = Master.SIM900.ask(Master.ThermSlot1, 'TVAL? 1') #f_burner
            mainplate_temp = Master.SIM900.ask(Master.ThermSlot1,'TVAL? 2')
            he_pump_temp = Master.SIM900.ask(Master.ThermSlot1, 'TVAL? 3')
            heat_sw_temp = Master.SIM900.ask(Master.ThermSlot1, 'TVAL? 4')

            temp_data_str = [c_head_temp, film_burner_temp, mainplate_temp, he_pump_temp, heat_sw_temp]
            self.update_GUI_sig.emit(temp_data_str)
            self.sleep(1) #alter to vary time temps update

class CooldownThreadStage1(QtCore.QThread): #Stage 1 will apply 26V (63mA 1.57W) to pump heater to raise to 50k stable.
                                            #Head should cool to ~4K
    #signals
    def __init__(self, parent=None):
        super(CooldownThreadStage1, self).__init__(parent)

    def __del__(self):
        self.wait()

    def run(self):
        #Sets output channel 1 on PS
        Master.Keithley.write("INST:NSEL 1")
        #Master.Keithley.write("CURR 0.063")
        Master.Keithley.write('CHAN:OUTP ON')
        #Ramp the voltage to 26V slowly
        time_to_ramp = 300 #seconds
        volts_per_sec = 25/time_to_ramp
        voltage=0
        initial_ramp=True
        while voltage < 25:
            voltage += volts_per_sec
            if voltage>25:
                voltage=25
            Master.Keithley.write("VOLT %f" % voltage)
            self.sleep(1)
        while True:
            temp=float(Master.current_pump_temp)
            if temp > 48.0:
                Master.Keithley.write('CHAN:OUTP OFF')
                initial_ramp=False
            elif temp < 47.0:
                if initial_ramp==True:
                    pass
                else:
                   Master.Keithley.write("VOLT 2.5")
                   Master.Keithley.write('CHAN:OUTP ON')
            self.sleep(1)

        

class CooldownThreadStage2(QtCore.QThread): #Stage 2 after stage one killed (heater OFF). Heat switch will be slowly ramped to 6V and cooling will begin. 
    #signals
    def __init__(self, parent=None):
        super(CooldownThreadStage2, self).__init__(parent)

    def __del__(self):
        self.wait()

    def run(self):
        #Waits 5 mins after heater set to OFF
        self.sleep(300)
        #Sets output channel 2 on PS
        Master.Keithley.write("INST:NSEL 2")
        Master.Keithley.write('CHAN:OUTP ON')
        #Ramp the voltage to 6V slowly
        time_to_ramp = 300 #seconds
        volts_per_sec = 6/time_to_ramp
        voltage=0
        while voltage < 6:
            voltage += volts_per_sec
            if voltage>6:
                voltage=6
            Master.Keithley.write("VOLT %f" % voltage)
            self.sleep(1)
        
####################

####################
# Run it
app = QtWidgets.QApplication(sys.argv)
Master = MainWindow()
Master.show()
sys.exit(app.exec_())
####################