#!/usr/bin/env python3

#    CPT 0.5.0

#    CPT - provides a gui to flash the ubports project to the all stable
#    devices. It started out as a tool to flash the Fairphone 2
#    Copyright (C) 2017  Smoose B.V. - Allaert Euser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
# 
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import threading
import gi
import tarfile
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import urllib.request
import json
from shutil import rmtree
from cpt_devices import all_devices

# check if we run in pyinstaller bundle and set currentdir accordingly
if getattr(sys, 'frozen', False):
    currentdir = os.path.dirname(sys._MEIPASS)
    print('packaged currentdir: %s' % currentdir)
else:
    print('not packaged')
    currentdir = './' + os.path.dirname(__file__)
# define a stage global to keep track of work
stage = -2
debugging = True
# quick and dirty define globals for boot and recovery images
#imgsurl = 'http://ci.ubports.com/job/daily-fp2/lastSuccessfulBuild/artifact/device_FP2_devel.tar.xz'
cachedir = os.path.expanduser('~/.cpt/cache/')
channel = 'stable'
device_name = ''
device = -1

GObject.threads_init()

def print_debug(msg):
    if debugging == True:
        print(msg)

class WorkerThread(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback
        self.stop_event = threading.Event()
    
    def initcache(self):
        global cachedir
        if os.path.isdir(cachedir):
            rmtree(cachedir, ignore_errors=True)
        os.makedirs(cachedir)

    def run(self):
        global stage
        global channel
        global device
        if stage == -2:
            self.initcache()
            stage = -1
        if stage == -1:
            if device !=-1:
                stage = 0
        if stage == 0:
            if self.fastboot('ping'):
                print_debug('fastboot returned device setting stage to 1')
                stage = 1
        elif stage == 1:
            if self.fastboot('format'):
                print_debug('fastboot format returned True, going to stage 1.5')
                d = self.fastboot('imgdownload')
                b = self.fastboot('flashboot')
                r = self.fastboot('flashrecovery')
                if b and r and d:
                    print_debug('fastboot flash both returned True, setting stage to 2')
                    stage = 2
        elif stage == 2 or stage == 3:
            if not self.adb('start'):
                print_debug('something is wrong with adb. please reinstall')
                stage = 9
            if not self.adb('ping'):
                print_debug('adb returned no device')
                stage = 3
            else:
                if self.adb('adbflash'):
                    print_debug('ubuntu touch flash success')
                    stage = 9
        # stage -2 - initcache
        # stage -1 - check if  device choice has been made
        # stage 0  - check if device is available in fastboot 
        # stage 1  - fastboot format and flash boot / recovery 
        # stage 2  - ready to flash ubuntu
        # stage 3  - no recovery image detected
        # stage 9  - end
        GObject.idle_add(self.callback)

    def create_ubuntu_command(self, downloadcache):
        dname = all_devices[device].name
        length = len(dname)
        contents = 'format system\nload_keyring image-master.tar.xz image-master.tar.xz.asc\nload_keyring image-signing.tar.xz image-signing.tar.xz.asc\nmount system\n'
        for file in os.listdir(downloadcache):
            if file[0:7] == 'ubports' and file[-3:] == '.xz':
                ubuntufile = file
            elif file[0:7] == 'ubports' and file[-3:] == 'asc':
                ubuntuascfile = file
            elif (file[0:7] == 'device-' or file[0:length] == dname) and file[-3:] == '.xz':
                devicefile = file
            elif (file[0:7] == 'device-' or file[0:length] == dname) and file[-3:] == 'asc':
                deviceascfile = file
            elif file[0:7] == 'keyring' and file[-3:] == '.xz':
                keyringfile = file
            elif file[0:7] == 'keyring' and file[-3:] == 'asc':
                keyringascfile = file
            elif file[0:7] == 'version' and file[-3:] == '.xz':
                versionfile = file
            elif file[0:7] == 'version' and file[-3:] == 'asc':
                versionascfile = file

        contents = contents + 'update ' + ubuntufile + ' ' + ubuntuascfile + '\n'
        contents = contents + 'update ' + devicefile + ' ' + deviceascfile + '\n'
        contents = contents + 'update ' + keyringfile + ' ' + keyringascfile + '\n'
        contents = contents + 'update ' + versionfile + ' ' + versionascfile + '\n'
        contents = contents + 'umount system\n'
        print_debug('ubuntu_command built')
        print_debug(contents)
        # either return contents or create file in downloadcache
        ucfile = downloadcache + '/ubuntu_command'
        ucf = open(ucfile ,'w', newline='\n')
        ucf.write(contents)
        ucf.close()
        return ucfile


    def adb(self, cmd):
        """Call adb with different commands"""
        # check adb if device is available and if device
        # is what is being expected ie FP2
        # adb devices
        # adb shell
        # adb push
        # adb reboot
        global device_name
        global channel
        global cachedir
        global currentdir
        dname = all_devices[device].name

        # make cross platform choice of tool
        if sys.platform == 'win32':
            adbcmd = 'bin\\adb.exe'
        elif sys.platform == 'linux':
            adbcmd = 'adb'
        elif sys.platform == 'darwin':
            adbcmd = currentdir + '/MacOS/bin/adb'
        else:
            adbcmd = 'adb'

        result = False
        if cmd == 'start':
            try:
                discard = os.popen(adbcmd + ' start-server').read().strip()
                result = True
            except:
                result = False
        if cmd == 'ping':
            try:
                output = os.popen(adbcmd +' shell getprop ro.product.device').read().strip()
                print_debug(output)
                if output != dname:
                    result = False
                    device_name = 'NONE'
                else:
                    result = True
                    device_name = dname
            except:
                device_name = 'NONE'
        if cmd == 'adbflash':
            if device_name == dname:
                # figure out how json files on server select the downloads mentioned below
                # get index.json
                url = 'http://system-image.ubports.com/ubports-touch/15.04/%s/%s/index.json' % (channel, device_name)
                indexfile = cachedir + '/index.json'
                req = urllib.request.urlretrieve(url, indexfile)
                data = json.load(open(indexfile))
                maxversion = 0
                listcount = 0
                lc = 0
                for i in data['images']:
                    if i['type'] == 'full':
                        if maxversion < i['version']:
                            maxversion = i['version']
                            lc = listcount
                    listcount = listcount + 1
                todownload = []
                for i in data['images'][lc]['files']:
                    todownload.append(i['path'])
                    todownload.append(i['signature'])
                progress_counter = 0.25
                progress_incr = 0.65 / (len(todownload)*2)
                for dl in todownload:
                    progress_counter = progress_counter + progress_incr
                    url = 'http://system-image.ubports.com' + dl
                    print_debug('Downloading ' + url)
                    win.progress.set_text('Downloading %s' % dl.split('/')[-1])
                    localfile = cachedir + '/' + dl.split('/')[-1]
                    req = urllib.request.urlretrieve(url, localfile)
                    win.progress.set_fraction(progress_counter)
                    win.progress.set_text('Pushing %s' % dl.split('/')[-1])
                    print_debug('Pushing ' + dl.split('/')[-1] + ' to device')
                    discard=os.popen(adbcmd + ' push ' + localfile + ' /cache/recovery/').read().strip()
                    progress_counter = progress_counter + progress_incr
                    win.progress.set_fraction(progress_counter)
                
                win.progress.set_text('Downloading gpg keys')
                for url in ['http://system-image.ubports.com/gpg/image-master.tar.xz','http://system-image.ubports.com/gpg/image-master.tar.xz.asc','http://system-image.ubports.com/gpg/image-signing.tar.xz','http://system-image.ubports.com/gpg/image-signing.tar.xz.asc']:
                    localfile = cachedir + '/' + url.split('/')[-1]
                    req = urllib.request.urlretrieve(url, localfile)
                    discard=os.popen(adbcmd + ' push ' + localfile + ' /cache/recovery/').read().strip()
                win.progress.set_fraction(0.95)
                ucfile = self.create_ubuntu_command(cachedir)
                discard=os.popen(adbcmd + ' push ' + ucfile + ' /cache/recovery/').read().strip()
                discard=os.popen(adbcmd + ' reboot recovery').read().strip()
                win.progress.set_text('Rebooting Device')
                win.progress.set_fraction(1.0)
                result = True
        return result
    

    def fastboot(self, cmd, img='NONE'):
        """Call fastboot with different commands"""
        global imgbooturl
        global imgrecoveryurl
        global cachedir
        global currentdir
        result = False
        if sys.platform == "win32":
            fbcmd = 'bin\\fastboot.exe'
        elif sys.platform == "linux":
            fbcmd = '/usr/bin/fastboot'
        elif sys.platform == 'darwin':
            fbcmd = currentdir + '/MacOS/bin/fastboot'
            print_debug(fbcmd)
        else:
            fbcmd = 'fastboot'
        
        # check OS and branch into OS specific fastboot
        # fastboot
        # format cache
        # format userdata
        # format system
        # reboot-bootloader
        # flash recovery
        # flash boot
        # imgdownload

        if cmd == 'imgdownload':
            imgsurl = all_devices[device].recovery
            friendlyname = all_devices[device].friendly
            if not os.path.isdir(cachedir):
                os.makedirs(cachedir)

            # do the image download stuff and tar stuff
            win.progress.set_text('Downloading %s images' % friendlyname)
            req = urllib.request.urlretrieve(imgsurl, cachedir + '/device.tar.xz')
            win.progress.set_fraction(0.15)
            win.progress.set_text('Unpacking %s images' % friendlyname)
            # untar the stuff and rename to bootfp2.img and recoveryfp2.img
            f = tarfile.open(cachedir + "/device.tar.xz", "r:xz")
            f.extract('partitions/boot.img', cachedir)
            f.extract('partitions/recovery.img', cachedir)
            # set progress
            win.progress.set_fraction(0.17)
            result = True

        elif cmd == 'flashboot':
            friendlyname = all_devices[device].friendly
            win.progress.set_text('Flashing %s Images' % friendlyname )
            try:
                win.progress.set_text('Flashing boot image')
                discard=os.popen(fbcmd + ' flash boot ' + cachedir + '/partitions/boot.img').read().strip()
                win.progress.set_fraction(0.17)
                result = True
            except:
                print_debug('flashing of boot image failed')
        elif cmd == 'flashrecovery':
            #cachedir = os.path.expanduser('~/.cpt/cache')
            #if not os.path.isdir(cachedir):
            #    os.makedirs(cachedir)
            #win.progress.set_text('Downloading recovery image')
            #req = urllib.request.urlretrieve(imgrecoveryurl, cachedir + '/partitions/recovery.img')
            win.progress.set_fraction(0.2)
            try:
                win.progress.set_text('Flashing recovery image')
                discard=os.popen(fbcmd + ' flash recovery ' + cachedir +'/partitions/recovery.img').read().strip()
                win.progress.set_fraction(0.25)
                result = True
            except:
                print_debug('flashing of recovery image failed')
        elif cmd == 'format':
            formatlist = ['cache', 'userdata', 'system']
            incr = 0.0416
            count = 0.0
            for fs in formatlist:
                count = count +  incr
                win.progress.set_text('Formatting %s' % fs)
                try:
                    discard=os.popen(fbcmd + ' format ' + fs).read().strip()
                except:
                    print_debug('format failed at %s' % fs)
                    break
                win.progress.set_fraction(count)
            try:
                discard=os.popen(fbcmd + ' reboot-bootloader').read().strip()
                win.progress.set_fraction(0.125)
                result = True
            except:
                print_debug('reboot failed')
        elif cmd == 'ping':
            msg = ''
            msg = os.popen(fbcmd + ' devices').read().strip()
            print_debug('the message is -->' + msg + '<--')
            if msg != '':
                result = True
        return result


        def stop(self):
            if self.isAlive() == True:
                self.stop_event.set()
                self.join()


        #Object.idle_add(self.callback)

class CPTMainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Ubuntu Touch Installer - CPT", border_width=8, resizable=False)
        #self.set_default_size(850, 500)
        obox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 25)
        vbox.set_homogeneous(False)
        hbox = Gtk.Box(spacing = 25)
        hbox.set_homogeneous(True)
        hbox2 = Gtk.Box(spacing = 25)
        hbox2.set_homogeneous(True)

        obox.pack_start(vbox, True, True, 0)
        obox.pack_start(hbox, True, True, 0)
        obox.pack_start(hbox2, True, True, 0)

        hbox_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)
        hbox_left.set_homogeneous(False)
        hbox_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)
        hbox_right.set_homogeneous(False)
       
        hbox.pack_start(hbox_left, True, True, 0)
        hbox.pack_start(hbox_right, True, True, 0)


        self.device_label = Gtk.Label('Device: ', xalign=0 )
        self.flash_label = Gtk.Label('', xalign=0)
        self.ubuntu_label = Gtk.Label('', xalign=0)

        vbox.pack_start(self.device_label, True, True, 0)
        vbox.pack_start(self.flash_label, True, True, 0)
        vbox.pack_start(self.ubuntu_label, True, True, 0)
    
        device_choice = Gtk.Label('Choose your device', xalign=0)
        
        count = 0
        device_store = Gtk.ListStore(int, str)
        while count < len(all_devices):
            print_debug('Adding device ' + str(count) + ' named ' + all_devices[count].friendly + ' to store')
            device_store.append([count, all_devices[count].friendly])
            count = count + 1

        self.device_choice_combox = Gtk.ComboBox.new_with_model(device_store)
        self.device_choice_combox.connect("changed", self.on_combox_change)
        #device_choice_combox.set_entry_text_column(1)
        render_text = Gtk.CellRendererText()
        self.device_choice_combox.pack_start(render_text, True)
        self.device_choice_combox.add_attribute(render_text, "text", 1)


        #channel_label = Gtk.Label('Choose your channel', xalign=0)

        #self.channel_button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Stable (stable)")
        #self.channel_button1.connect("toggled", self.on_button_toggled, "stable")
        #self.channel_button2 = Gtk.RadioButton.new_with_label_from_widget(self.channel_button1, "Release Candidate (rc)")
        #self.channel_button2.connect("toggled", self.on_button_toggled, "rc")
        #self.channel_button3 = Gtk.RadioButton.new_with_label_from_widget(self.channel_button1, "Nightly Build (devel)")
        #self.channel_button3.connect("toggled", self.on_button_toggled, "devel")
        #self.channel_button4 = Gtk.RadioButton.new_with_label_from_widget(self.channel_button1, "Experimental (devel-proposed)")
        #self.channel_button4.connect("toggled", self.on_button_toggled, "devel-proposed")
        #self.channel_button5 = Gtk.RadioButton.new_with_label_from_widget(self.channel_button1, "Nightly (devel_rc-proposed)")
        #self.channel_button5.connect("toggled", self.on_button_toggled, "devel_rc-proposed")

        self.exp_label = Gtk.Label('',xalign=0)
        
        self.exp_label.set_markup('<span weight="bold">For Fairphone:</span> Connect your device and boot into\n'
                                   '<span style="italic">fastboot</span> mode. Hold volume down and push the power\n'
                                   'button. Release when the phone vibrates.\n\n'
                                   '<span weight="bold">For Nexus 5:</span> Connect your device and boot into\n'
                                   '<span style="italic">fastboot</span> mode. Hold volume up, down and push the\n'
                                   'power button. Release when <span style="italic">fastboot</span> menu is shown.\n\n'
                                   '<span weight="bold">For OnePlus One:</span> Connect your device and boot into\n'
                                   '<span style="italic">fastboot</span> mode. Hold volume up and push the power\n'
                                   'button. Release when the text <span style="italic">fastboot</span> is shown.')
        #self.status_label = Gtk.Label('', xalign=0)
        self.progress = Gtk.ProgressBar()
        self.progress.set_text('')
        self.progress.set_show_text(True)
       
        hbox_left.pack_start(device_choice, False, False, 0)
        hbox_left.pack_start(self.device_choice_combox, False, False, 0)
        #hbox_left.pack_start(channel_label, False, False, 0)
        #hbox_left.pack_start(self.channel_button1, False, False, 0)
        #hbox_left.pack_start(self.channel_button2, False, False, 0)
        #hbox_left.pack_start(self.channel_button3, False, False, 0)
        #hbox_left.pack_start(self.channel_button4, False, False, 0)
        #hbox_left.pack_start(self.channel_button5, False, False, 0)
        hbox_left.pack_start(self.exp_label, False, False, 0)
        
        #hbox2.pack_start(self.status_label, False, False, 0)

        self.spinner = Gtk.Spinner()
        self.action_button1 = Gtk.Button(label = "Start")
        self.action_button1.connect("clicked", self.on_button_clicked)

        logo = Gtk.Image()
        if sys.platform != 'darwin':
            logo.set_from_file('gfx/ubrobot.png')


        hbox_right.pack_start(logo, False, False, 0)
        hbox_right.pack_start(self.spinner, False, False, 0)
        hbox_right.pack_start(self.action_button1, False, False, 0)

        obox.pack_start(self.progress, False, False, 0)
        self.add(obox)

    def on_button_clicked(self, widget):
        global stage
        print_debug("Button Clicked at stage %s" % stage)
        self.spinner.start()
        if stage == 1:
            #self.status_label.set_markup('<span foreground="blue">Flashing recovery image</span>')
            self.progress.set_text('Flashing recovery image')
            self.device_choice_combox.set_sensitive(False)
        elif stage == 2 or stage == 3:
            #self.channel_button1.set_sensitive(False)
            #self.channel_button2.set_sensitive(False)
            #self.channel_button3.set_sensitive(False)
            #self.channel_button4.set_sensitive(False)
            #self.channel_button5.set_sensitive(False)
            self.action_button1.set_sensitive(False)
            self.ubuntu_label.set_markup('<span foreground="blue">Ubuntu: Installing</span>')
            self.progress.set_text('Installing Ubuntu')
        thread = WorkerThread(self.work_finished_cb)
        print_debug("Starting WorkerThread")
        thread.start()

    def on_button_toggled(self, button, name):
        global channel
        if button.get_active():
            print_debug('radio button channel %s switch on' % name)
            channel = name
        else:
            print_debug('radio button channel %s switch off' % name)
        channel = name
            

                
        return True   

    def on_combox_change(self, combo):
        global device
        t = combo.get_active_iter()
        if t != None:
            model = combo.get_model()
            print_debug('combobox item %s named %s is active' % (model[t][0], model[t][1]))
            device = int(model[t][0])
            
    def work_finished_cb(self):
        #12345678901234567890123456789012345678901234567
        global stage
        if stage == -1:
            self.progress.set_text('Choose the device you have')
            
        if stage == 0:
            #self.status_label.set_markup('<span foreground="red">Please make sure a device is connected and set to fastboot mode</span>')
            self.progress.set_text('Please make sure a device is connected and set to fastboot mode')
            self.device_label.set_markup('<span foreground="red">Device: NOT FOUND</span>')
            self.device_choice_combox.set_sensitive(False)
        elif stage == 1:
            #self.status_label.set_markup('<span foreground="green">Device detected and booted to fastboot mode</span>')
            self.progress.set_text('Device detected and booted to fastboot mode')
            self.device_label.set_markup('<span foreground="green">Device: FOUND</span>')
            self.exp_label.set_markup('\nDevice detected.\n'
                                      '<span weight="bold">WARNING!</span>\n'
                                      'All data will be deleted from your device.\n'
                                      'Please make sure you have a backup of your data.\n'
                                      'Continue at your own risk!')

            self.action_button1.set_label('Flash Device')
            self.device_choice_combox.set_sensitive(False)
        elif stage == 2:
            self.flash_label.set_markup('<span foreground="green">Recovery image flash: DONE</span>')
            self.progress.set_text('Recovery image successfully flashed')

            self.exp_label.set_markup('<span weight="bold">For Fairphone:</span> Boot into <span style="italic">recovery</span> mode. Hold\n'
                                      'volume up and push the power button. Release when\n'
                                      'the phone vibrates. And wait... Be patient...\n\n'
                                      '<span weight="bold">For Nexus 5:</span> Boot into <span style="italic">recovery</span> mode. Hold\n'
                                      'volume up, down and push the power button. Release\n'
                                      'when <span style="italic">fastboot</span> menu is shown. Select <span style="italic">recovery</span> mode\n'
                                      'with volume buttons and confirm with power button.\n\n'
                                      '<span weight="bold">For OnePlus One:</span> Boot into <span style="italic">recovery</span> mode. Hold\n'
                                      'volume down and push the power button. Release when\n'
                                      'the recovery options are shown.')
            self.action_button1.set_label('Install Ubuntu')
            self.progress.set_fraction(0.3)
        elif stage == 3:
            #self.status_label.set_markup('<span foreground="red">Could not detect device in recovery mode.</span>')
            self.progress.set_text('Could not detect device in recovery mode.')
            self.ubuntu_label.set_markup('<span foreground="blue">Device in recovery mode: NOT FOUND</span>')
            #self.channel_button1.set_sensitive(True)
            #self.channel_button2.set_sensitive(True)
            #self.channel_button3.set_sensitive(True)
            #self.channel_button4.set_sensitive(True)
            #self.channel_button5.set_sensitive(True)
            self.action_button1.set_sensitive(True)
        elif stage == 9:
            #self.status_label.set_markup('<span foreground="green">Ubuntu is installed on your device</span>')
            self.progress.set_text('Ubuntu is installed on your device')
            self.ubuntu_label.set_markup('<span foreground="green">Ubuntu: INSTALLED</span>')
            self.exp_label.set_text('\nUbuntu installation continues on your device\n'
                                    'Please follow instructions on your device\n\n\n')
            self.progress.set_fraction(1.0)
        self.spinner.stop()
        return

    

if __name__ == '__main__':
    win = CPTMainWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()



