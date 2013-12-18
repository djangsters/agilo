#!/usr/bin/env python

# Usage:
# 01. Be sure that this file is executable, otherwise open the shell and enter "chmod u+x <this_sript>"
# 02. To update the vm use this script as follows:
#    <this_script> <egg file>, i.e.
#    ./remote_update_virtualmachine agilo_dist.egg

# TODO
# * Detect connection errors. A working internet connection is needed by the vm update and upgrade process
# * Implement automated tests:
#     - Check that a trial license can be generated and activated
#     - Check that the *.vmx file hasn't changed (just diff it)
#     - MAC address should not change. It should be: 00:50:56:00:18:64 (if it did, you probably changed the VM in a way that it doesn't run with old versions of VMWare!)

# More info at https://dev.agile42.com/wiki/agilo/dev/UpdateVirtualMachine

# Setting needed parameters
VM_USER = "agilo"
VM_PASSWORD = "agile42"
VM_PORT = 22

# To set up an ssh forward use this "ssh -L 2222:172.16.29.128:22 <VM-HOST>"

###############################################################################

import sys
import pexpect
import os

os.environ.setdefault('LC_ALL', 'en_US.UTF-8')

if len(sys.argv) != 3:
    print "Usage: '%s <src_egg>' <vm-host>\n" % sys.argv[0]
    sys.exit(1)

EGG_NAME = sys.argv[1]
VM_IP = sys.argv[2]

#REFACT: Consider to check the input. If empty or not ending with *.egg -> return the same error.
if not os.path.isfile(EGG_NAME):
    print '%s is not a file' % EGG_NAME
    sys.exit(1)

def authenticate(process):
    process.expect("assword.*:")
    process.sendline(VM_PASSWORD)

def upload_file(a_file_path):
    scp = pexpect.spawn("scp", ["-P%s" % VM_PORT, a_file_path, "%s@%s:" % (VM_USER, VM_IP)])
    authenticate(scp)
    scp.expect(pexpect.EOF)

def run_command(process, a_command):
    process.sendline(a_command)
    process.expect('agilopro:')


# Copy local python egg for agilo to vm
upload_file(EGG_NAME)
script_dir = os.path.dirname(sys.argv[0])
updater = os.path.join(script_dir, 'update_virtual_machine.py')
upload_file(updater)
demo_data_creator = os.path.join(script_dir, 'create_demo_data.py')
upload_file(demo_data_creator)
disk_shrinker = os.path.join(script_dir, 'shrink_disk.sh')
upload_file(disk_shrinker)

ssh = pexpect.spawn('ssh', ["-p%s" % VM_PORT, '%s@%s' % (VM_USER, VM_IP)])
authenticate(ssh)
run_command(ssh, 'sudo -k')
ssh.sendline('sudo -s')
authenticate(ssh)

LOCAL_EGG_FILENAME = os.path.basename(EGG_NAME)
ssh.sendline('python update_virtual_machine.py %s' % LOCAL_EGG_FILENAME)
ssh.interact()
