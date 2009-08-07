#!/usr/bin/env python

import sys

try:
     import pygtk
     pygtk.require("2.0")
except:
      pass
try:
    import gtk
    import gtk.glade
    import os
    import commands
    import threading
    import datetime
    import gettext
    from user import home
except:
    print "You do not have all the dependencies!"
    sys.exit(1)

gtk.gdk.threads_init()
from subprocess import Popen, PIPE

architecture = commands.getoutput("uname -a")
if (architecture.find("x86_64") >= 0):
	import ctypes
	libc = ctypes.CDLL('libc.so.6')
	libc.prctl(15, 'mint-debian-installer', 0, 0, 0)	
else:
	import dl
	libc = dl.open('/lib/libc.so.6')
	libc.call('prctl', 15, 'mint-debian-installer', 0, 0, 0)

# i18n
gettext.install("messages", "/usr/lib/linuxmint/mint-debian-installer/locale")

class Choices:
	name = None
	username = None
	password = None
	hostname = None
	grub = None
	grubIsToBeInstalled = True
 	partition = None

	def __init__(self):
		pass

class PerformInstall(threading.Thread):

	def __init__(self, wTree, choices):
		threading.Thread.__init__(self)		
		self.wTree = wTree		
		self.choices = choices

	def run(self):
		try:				

			self.numSteps = 12

			gtk.gdk.threads_enter()
			gladefile = "/usr/lib/linuxmint/mint-debian-installer/mint-debian-installer.glade"
			self.progressTree = gtk.glade.XML(gladefile,"progress_window")
			self.progresswindow = self.progressTree.get_widget("progress_window")
			self.progresswindow.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
			self.progresswindow.set_title("")
			self.progresslabel = self.progressTree.get_widget("progress_label")
			self.progressbar = self.progressTree.get_widget("progressbar")			
			self.progresswindow.show()
			gtk.gdk.threads_leave()

			self.progress(0)

			self.report("Formatting " + self.choices.partition + " with ext3")
			os.system("umount " + self.choices.partition)
			os.system("mkfs.ext3 " + self.choices.partition)
			self.progress(1)

			self.report("Preparing /target")			
			os.system("mkdir -p /target")
			os.system("umount /target")
			os.system("rm -rf /target/*")
			self.progress(2)

			self.report("Mounting " + self.choices.partition + " in /target")
			os.system("mount " + self.choices.partition + " /target")
			self.progress(3)

			self.report("Copying file system to /target")
			os.system("rsync -a / /target/ --exclude=/{target,live,sys,proc,media}/")
			self.progress(4)

			self.report("Creating system mount points for proc, sys, media")
			os.system("mkdir -p /target/proc /target/sys /target/media")
			self.progress(5)

			self.report("Chrooting into /target")
			os.chroot("/target/")	
			if (self.choices.grubIsToBeInstalled):
				self.report("Installing Grub in " + self.choices.grub)
				os.system("grub-install " + self.choices.grub)
				self.report("Updating Grub")
				os.system("update-grub")
			self.progress(6)

			self.report("Setting up fstab")
			os.system("rm -rf /etc/fstab")
			os.system("echo \"proc	/proc	proc defaults	0	0\" > /etc/fstab")
			os.system("echo \"" + self.choices.partition + "	/	ext3	defaults	0	1\" >> /etc/fstab")
			self.progress(7)

			self.report("Setting up user " + self.choices.username)
			os.system("usermod -l " + self.choices.username + " self.choices.user")
			os.system("groupmod -n " + self.choices.username + " self.choices.user")
			os.system("usermod -d /home/" + self.choices.username + " -m " + self.choices.username)
			os.system("usermod -c \"" + self.choices.name + "\" " + self.choices.username)
			self.progress(8)

			self.report("Setting up sudo")
			os.system("sed 's/user/%admin/g' /etc/sudoers > /tmp/sudoers && mv /tmp/sudoers /etc/sudoers")
			os.system("chmod 0440 /etc/sudoers")
			os.system("groupadd admin")
			os.system("usermod -a -G admin " + self.choices.username)
			self.progress(9)

			self.report("Setting up password")
			os.system("echo \"" + self.choices.username + ":" + self.choices.password + "\" > /tmp/password")
			os.system("cat /tmp/password | chpasswd")
			self.progress(10)

			self.report("Setting up the hostname: " + self.choices.hostname)
			os.system("echo '" + self.choices.hostname + "' > /etc/hostname")
			os.system("hostname " + self.choices.hostname)
			os.system("sed 's/debian/"+ self.choices.hostname + "/g' /etc/hosts > /tmp/hosts && mv /tmp/hosts /etc/hosts")
			self.progress(11)

			self.report("Removing mint-debian-installer from the target system")
			os.system("rm -rf /home/" + self.choices.username + "/Desktop/mint-debian-installer.desktop")
			os.system("apt-get remove mint-debian-installer --yes --force-yes")
			self.progress(12)

			self.report("Finished")
						
			gtk.gdk.threads_enter()
			self.progresswindow.hide()			
			gtk.gdk.threads_leave()

			dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_NONE, _("Linux Mint Debian Edition was successfully installed on your computer. You can now eject the CD and reboot the system."))
			dialog.set_title(_("mint-debian-installer"))
			dialog.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
			dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
			dialog.connect('response', lambda dialog, response: self.closeApp())
			dialog.show()	

		except Exception, detail:	
			print detail		
			dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_NONE, _("An error occurred during the installation:") + " " + str(detail))
			dialog.set_title(_("mint-debian-installer"))
			dialog.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
			dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
			dialog.connect('response', lambda dialog, response: self.closeApp())
			dialog.show()			

	def closeApp(self):
		gtk.main_quit()

	def report(self, text):
		print text
		gtk.gdk.threads_enter()	
		self.progresslabel.set_text(text)
		gtk.gdk.threads_leave()

	def progress(self, step):
		#import time
		#time.sleep(5)
		fraction = float(step)/float(self.numSteps)
		gtk.gdk.threads_enter()
		self.progressbar.set_fraction(fraction)
		gtk.gdk.threads_leave()

class mainWindow:
    """This is the main class for the application"""

    def __init__(self):
	#Set the Glade file
        self.gladefile = "/usr/lib/linuxmint/mint-debian-installer/mint-debian-installer.glade"
        self.wTree = gtk.glade.XML(self.gladefile,"main_window")
	self.wTree.get_widget("main_window").connect("destroy", gtk.main_quit)
	self.wTree.get_widget("main_window").set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
	self.wTree.get_widget("main_window").set_title(_("Installer"))

	self.wTree.get_widget("button_forward_1").connect('clicked', self.next_page)
	self.wTree.get_widget("button_forward_2").connect('clicked', self.validate_partition)
	self.wTree.get_widget("button_forward_3").connect('clicked', self.validate_names)
	self.wTree.get_widget("button_forward_4").connect('clicked', self.last_page)
	self.wTree.get_widget("button_apply").connect('clicked', self.performInstall)

	self.wTree.get_widget("button_back_2").connect('clicked', self.prev_page)
	self.wTree.get_widget("button_back_3").connect('clicked', self.prev_page)
	self.wTree.get_widget("button_back_4").connect('clicked', self.prev_page)
	self.wTree.get_widget("button_back_5").connect('clicked', self.prev_page)

	self.wTree.get_widget("button_quit_1").connect('clicked', gtk.main_quit)
	self.wTree.get_widget("button_quit_2").connect('clicked', gtk.main_quit)
	self.wTree.get_widget("button_quit_3").connect('clicked', gtk.main_quit)
	self.wTree.get_widget("button_quit_4").connect('clicked', gtk.main_quit)
	self.wTree.get_widget("button_quit_5").connect('clicked', gtk.main_quit)

	self.wTree.get_widget("menu_quit").connect('activate', gtk.main_quit)
	self.wTree.get_widget("menu_about").connect('activate', self.open_about)	

	self.tree = self.wTree.get_widget("treeview_hard_disks")
	self.column = gtk.TreeViewColumn(_("Disk"))
        self.tree.append_column(self.column)
        self.renderer = gtk.CellRendererText()
        self.column.pack_start(self.renderer, True)
        self.column.add_attribute(self.renderer, 'text', 0)        
	self.model = gtk.ListStore(str)		

	# Find hard-drives
	hdd_descriptions = []
	inxi = commands.getoutput("inxi -D -c 0")
	parts = inxi.split(":")
	for part in parts:		
		if "/dev/" in part:
			hdd = part[:-1].strip()
			self.model.append([hdd])

	self.tree.set_model(self.model)
	self.tree.show()

	self.tree = self.wTree.get_widget("treeview_partitions")
	self.renderer = gtk.CellRendererText()

	self.column1 = gtk.TreeViewColumn(_("Partition"))
        self.column1.pack_start(self.renderer, True)
        self.column1.add_attribute(self.renderer, 'text', 0)        
        self.tree.append_column(self.column1)        

	self.column2 = gtk.TreeViewColumn(_("Size"))
        self.column2.pack_start(self.renderer, True)
        self.column2.add_attribute(self.renderer, 'text', 1)        
        self.tree.append_column(self.column2)        

	self.column3 = gtk.TreeViewColumn(_("Type"))
        self.column3.pack_start(self.renderer, True)
        self.column3.add_attribute(self.renderer, 'text', 2)        
        self.tree.append_column(self.column3)

	self.model = gtk.ListStore(str, str, str, str)
	partitions = commands.getoutput("fdisk -l")
	partitions = partitions.split("\n")
	for partition in partitions:
		if "/dev/" in partition:
			parts = partition.split()
			if len(parts) >= 6:				
				if "/dev/" in parts[0]:
					# Partition
					device = parts[0]
					bootable = False
					x = 1
					if parts[1] == "*":
						bootable = True	
						x = x + 1
					start = parts[x]
					end = parts[x+1]
					blocks = parts[x+2]
					try: 
						if blocks[-1:] == "+":
							blocks = blocks[:-1]
						blocks = int(blocks) / 1024 / 1024
						blocks = str(blocks) + _("GB")
					except Exception, detail:
						print detail
						pass
					code_type = (parts[x+3]).strip()
					str_type = ""			
					for subpart in parts[x+4:]:	
						str_type = str_type + subpart + " "						
						
					self.model.append([device, blocks, str_type, code_type])					
	self.tree.set_model(self.model)
	self.tree.show()

    def prev_page(self, widget):
	self.wTree.get_widget("notebook").prev_page()

    def next_page(self, widget):
	self.wTree.get_widget("notebook").next_page()

    def last_page(self, widget):
	self.update_summary()
	self.next_page(widget)

    def validate_partition(self, widget):
	# Need to have a partition selected
	(model, iter) = self.wTree.get_widget("treeview_partitions").get_selection().get_selected()
	if iter is None:
		dialog = gtk.MessageDialog(self.wTree.get_widget("main_window"), gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_NONE, _("Please select a partition"))
		dialog.set_title(_("mint-debian-installer"))
		dialog.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
		dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
		dialog.connect('response', lambda dialog, response: dialog.destroy())
		dialog.show()
	else:
		# Selection needs to be a Linux partition
		partition_type = model.get_value(iter, 3)
		if partition_type == "83":
			self.next_page(widget)
		else:
			dialog = gtk.MessageDialog(self.wTree.get_widget("main_window"), gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_NONE, _("The type of partition you selected isn't suitable. Please select a Linux partition."))
			dialog.set_title(_("mint-debian-installer"))
			dialog.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
			dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
			dialog.connect('response', lambda dialog, response: dialog.destroy())
			dialog.show()	

    def validate_names(self, widget):
	
	valid = True
	errorMsg = ""
	widget_focus = None
	# Need to have data in each field
	name = self.wTree.get_widget("entry_name").get_text().strip()
	username = self.wTree.get_widget("entry_username").get_text().strip()
	password1 = self.wTree.get_widget("entry_password1").get_text().strip()
	password2 = self.wTree.get_widget("entry_password2").get_text().strip()
	hostname = self.wTree.get_widget("entry_hostname").get_text().strip()
	
	if len(name) == 0:
		valid = False
		errorMsg = _("Please indicate your name")
		widget_focus = self.wTree.get_widget("entry_name")
	elif len(username) == 0:
		valid = False
		errorMsg = _("Please choose a username")
		widget_focus = self.wTree.get_widget("entry_username")
	elif password1 != password2:
		valid = False
		errorMsg = _("You entered two different passwords")
		self.wTree.get_widget("entry_password1").set_text("")
		self.wTree.get_widget("entry_password2").set_text("")
		widget_focus = self.wTree.get_widget("entry_password1")
	elif len(password1) == 0:
		valid = False
		errorMsg = _("Please choose a password")
		widget_focus = self.wTree.get_widget("entry_password1")
	elif len(hostname) == 0:
		valid = False
		errorMsg = _("Please choose a hostname")
		widget_focus = self.wTree.get_widget("entry_hostname")
	
	if not valid:
		dialog = gtk.MessageDialog(self.wTree.get_widget("main_window"), gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_NONE, errorMsg)
		dialog.set_title(_("mint-debian-installer"))
		dialog.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
		dialog.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
		dialog.connect('response', lambda dialog, response: dialog.destroy())
		dialog.show()
		widget_focus.grab_focus()
	else:
		self.next_page(widget)

    def update_summary(self):
	self.wTree.get_widget("label_summary_name").set_text(_("Your name is <b>%s</b>") % (self.wTree.get_widget("entry_name").get_text()))
	self.wTree.get_widget("label_summary_name").set_use_markup(True)
	self.wTree.get_widget("label_summary_username").set_text(_("Your username will be <b>%s</b>") % (self.wTree.get_widget("entry_username").get_text()))
	self.wTree.get_widget("label_summary_username").set_use_markup(True)
	self.wTree.get_widget("label_summary_hostname").set_text(_("Your computer will be called <b>%s</b>") % (self.wTree.get_widget("entry_hostname").get_text()))
	self.wTree.get_widget("label_summary_hostname").set_use_markup(True)
	self.wTree.get_widget("label_summary_grub").set_text(_("The grub bootloader will be installed in <b>%s</b>") % (self.wTree.get_widget("entry_grub").get_text()))
	self.wTree.get_widget("label_summary_grub").set_use_markup(True)
	(model, iter) = self.wTree.get_widget("treeview_partitions").get_selection().get_selected()
	value = model.get_value(iter, 0)
	self.wTree.get_widget("label_summary_partition").set_text(_("Linux Mint Debian edition will be installed in <b>%s</b>") % (value))
	self.wTree.get_widget("label_summary_partition").set_use_markup(True)

    def performInstall(self, widget):
	# Hide main window
	self.wTree.get_widget("main_window").hide()
	# Get choices
	choices = Choices()
	choices.name = self.wTree.get_widget("entry_name").get_text().strip()
	choices.username = self.wTree.get_widget("entry_username").get_text().strip()
	choices.password = self.wTree.get_widget("entry_password1").get_text().strip()
	choices.hostname = self.wTree.get_widget("entry_hostname").get_text().strip()
	choices.grub = self.wTree.get_widget("entry_grub").get_text().strip()
	choices.grubIsToBeInstalled = self.wTree.get_widget("check_grub").get_active()
	(model, iter) = self.wTree.get_widget("treeview_partitions").get_selection().get_selected()
	choices.partition = model.get_value(iter, 0)
	install = PerformInstall(self.wTree, choices)
	install.start()	

    def open_about(self, widget):
	dlg = gtk.AboutDialog()
	dlg.set_title(_("About") + " - mint-debian-installer")
	dlg.set_program_name("mint-debian-installer")
	dlg.set_comments(_("Installer"))
        try:
		h = open('/usr/share/common-licenses/GPL','r')
		s = h.readlines()
		gpl = ""
		for line in s:
			gpl += line
		h.close()
		dlg.set_license(gpl)
        except Exception, detail:
        	print detail
	try: 
		version = commands.getoutput("/usr/lib/linuxmint/mint-debian-installer/version.py")
		dlg.set_version(version)
	except Exception, detail:
		print detail

        dlg.set_authors(["Clement Lefebvre <root@linuxmint.com>"]) 
	dlg.set_icon_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png")
	dlg.set_logo(gtk.gdk.pixbuf_new_from_file("/usr/lib/linuxmint/mint-debian-installer/icon.png"))
        def close(w, res):
            if res == gtk.RESPONSE_CANCEL:
                w.hide()
        dlg.connect("response", close)
        dlg.show()
	
if __name__ == "__main__":
	mainwin = mainWindow()
	gtk.main()

