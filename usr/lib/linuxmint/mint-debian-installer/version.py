#!/usr/bin/python

import apt
import sys

try:
	cache = apt.Cache()	
	pkg = cache["mint-debian-installer"]
	print pkg.installedVersion
except:
	pass


