#!/usr/bin/python

from dogtail import tree

gedit = tree.root.application("gedit")
gedit.child("Menu",                    roleName="toggle button").click()
gedit.child("Tools",                   roleName="push button")  .click()
gedit.child("Insert Date and Time...", roleName="push button")  .click()
gedit.child("Insert",                  roleName="push button")  .click()
