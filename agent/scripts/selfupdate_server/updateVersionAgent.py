#!/usr/bin/env python
"""This demonstrates a minimal http upload cgi.
This allows a user to upload up to three files at once.
It is trivial to change the number of files uploaded.

This script has security risks. A user could attempt to fill
a disk partition with endless uploads.
If you have a system open to the public you would obviously want
to limit the size and number of files written to the disk.
"""
import cgi
import cgitb; cgitb.enable()
import os
import json
import sys

try: # Windows needs stdio set for binary mode.
    import msvcrt
    msvcrt.setmode (0, os.O_BINARY) # stdin  = 0
    msvcrt.setmode (1, os.O_BINARY) # stdout = 1
except ImportError:
    pass

UPLOAD_DIR = "/domain/apache2/htdocs/agent_updates"

HTML_TEMPLATE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html><head><title>File Upload</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
</head><body><h1>File Upload</h1>
<form action="%(SCRIPT_NAME)s" method="POST" enctype="multipart/form-data">
Version: <input name="agent_version" type="text"><br>
Agent Cronus Package: <input name="agent_cronus" type="file"><br>
Agent Cronus Prop: <input name="agent_prop" type="file"><br>
Agent Config Cronus Package: <input name="agent_config_cronus" type="file"><br>
Agent Config Cronus Prop: <input name="agent_config_prop" type="file"><br>
<input name="submit" type="submit">
</form>
</body>
</html>"""

def print_html_form (description = None):
    """This prints out the html form. Note that the action is set to
      the name of the script which makes this is a self-posting form.
      In other words, this cgi both displays a form and processes it.
    """
    print "content-type: text/html\n"
    if description: print "%s" % description
    print HTML_TEMPLATE % {'SCRIPT_NAME':os.environ['SCRIPT_NAME']}

def save_uploaded_file (form_fields, upload_dir):
    """This saves a file uploaded by an HTML form.
       The form_field is the name of the file input field from the form.
       For example, the following form_field would be "file_1":
           <input name="file_1" type="file">
       The upload_dir is the directory where the file will be written.
       If no file was uploaded or if the field does not exist then
       this does nothing.
    """
    description = None
    form = cgi.FieldStorage()
    if not form.has_key('agent_version'): return description
    version = form['agent_version'].value
    path = os.path.join(UPLOAD_DIR, version)
    if not os.path.exists(path):
        os.mkdir(path, 0755)

    for form_field in form_fields:
        if not form.has_key(form_field): continue
        fileitem = form[form_field]
        if not fileitem.file: continue
        if not fileitem.filename: continue

        with file (os.path.join(path, fileitem.filename), 'wb') as fout:
            while 1:
                chunk = fileitem.file.read(100000)
                if not chunk: break
                fout.write (chunk)
            description = '%s%s uploaded\n' % (description, fileitem.filename)
    return description

description = save_uploaded_file (["agent_cronus","agent_prop","agent_config_cronus","agent_config_prop"], UPLOAD_DIR)
print_html_form (description)
