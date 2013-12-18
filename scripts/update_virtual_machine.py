#!/usr/bin/env python

import sys
from subprocess import check_call

def call(command, *args, **kwargs):
    try:
        command_with_args = [command] + list(args)
        print "Now running:", ' '.join(command_with_args)
        check_call(command_with_args, **kwargs)
    except Exception, e:
        print 'Got excpetion %s' % e
        sys.exit(1)


ENVIRONMENT_PATH = "/var/lib/trac/demo"
STATIC_RESOURCES_PATH = "/var/www/agilo_static/"

if len(sys.argv) == 2:
    TARGET_EGG_NAME = sys.argv[1]
else:
    print "An error occured! Please use the script as <scriptname> <target_egg>!"
    sys.exit(1)

# Update the vm so it stays current as root
call("apt-get", "update")

# Upgrading the vm so it stays current as root
call("apt-get", "upgrade", "-y", "--force-yes")

# Remove the old version of involved eggs so easy install can install the latest (supported) versions later
call("rm -vrf /usr/lib/python2.*/site-packages/*agilo*", shell=True)
# don't remove the "TracAccountManager"
# actually we could also try installing that one from svn every time 
# however easy_install http://<...> does not work - probably the old easy_install can't handle it
call("rm -vrf /usr/lib/python2.*/site-packages/Trac-*", shell=True)
call("rm -vrf /usr/lib/python2.*/site-packages/Genshi*", shell=True)

# Install the binary eggs in with easy_install (easy_install /path/to/egg)
call("easy_install", TARGET_EGG_NAME)

# upgrade environment
call('trac-admin', ENVIRONMENT_PATH, 'upgrade')

# re-deploy static resources with trac admin (first remove the target dir, then deploy again to it
call("rm", "-vrf", STATIC_RESOURCES_PATH)
call("trac-admin", ENVIRONMENT_PATH, "deploy", STATIC_RESOURCES_PATH)

# re-create the demo data (make sure you have the latest version from the repository!)
call("python", "create_demo_data.py", "--delete", "--env=%s" % ENVIRONMENT_PATH)

# Restart Trac by restarting Apache
call("/etc/init.d/apache2", "restart")


# Minify the virtual machine
call('apt-get', 'clean')
call('rm', '-f', '/home/agilo/.bash_history')
call('rm', '-f', '/home/agilo/.lesshst')
call('rm', '-f', '/home/agilo/.nano_history')

call("sh", "shrink_disk.sh")
