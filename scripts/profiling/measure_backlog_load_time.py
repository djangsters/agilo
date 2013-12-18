#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# This script calls the backlog page multiple times and measures the time until 
# the complete page is received.
# -----------------------------------------------------------------------------
# Configuration
port = 8011
sprint_name = None

mount_directory = None

username = None
password = None

number_of_requests = 10



# -----------------------------------------------------------------------------

from datetime import datetime
import urllib
import sys

from mechanize import Browser

from agilo.scrum import BACKLOG_URL


def build_trac_url(port, mount_directory):
    if mount_directory == None:
        mount_directory = ''
    elif mount_directory.endswith('/'):
        mount_directory = mount_directory[:-1]
    return 'http://localhost:%d/%s' % (port, mount_directory)

def build_backlog_url(trac_url, sprint_name):
    assert (sprint_name not in [None, '']), 'Please configure a sprint name!'
    sprint_name = urllib.quote_plus(sprint_name)
    url_template = '%s%s/Sprint+Backlog/%s'
    url = url_template % (trac_url, BACKLOG_URL, sprint_name)
    return url

def measure_backlog_load_time(browser, url, number_of_requests):
    measurements = []
    for i in range(number_of_requests):
        start = datetime.now()
        response = browser.open(url)
        response.read()
        end_time = datetime.now()
        delta = (end_time - start)
        nr_seconds = delta.seconds + float(delta.microseconds) / 1000000
        measurements.append(nr_seconds)
    return measurements

def do_login(browser, trac_url, username, password):
    if username != None and password != None:
        browser.add_password('%slogin' % trac_url, str(username), str(password))
        browser.open('%slogin' % trac_url)
        # login using the form
        for form in browser.forms():
            if form.attrs.get('id') == 'acctmgr_loginform':
                browser.form = form
                break
        
        browser.set_value(username, 'user')
        browser.set_value(password, 'password')
        browser.submit()
        print "Logged in as:", username

if __name__ == '__main__':
    trac_url = build_trac_url(port, mount_directory)
    if sprint_name == None:
        if len(sys.argv) > 1:
            sprint_name = sys.argv[1]
            username = sys.argv[2]
            password = sys.argv[3]
        else:
            print 'Usage ', sys.argv[0], ' sprint name'
            sys.exit(0)
    url = build_backlog_url(trac_url, sprint_name).replace('+', '%20')
    print "Starting measuring on:", url, "as:", username, password
    
    browser = Browser()
    do_login(browser, trac_url, username, password)
    measurements = measure_backlog_load_time(browser, url, number_of_requests)
    
    average = sum(measurements) / number_of_requests
    print 'Average time to process request: %0.2f seconds' % average
    if measurements[0] > average * 1.25:
        initial_overhead = (measurements[0] / average - 1) * 100
        msg = '    Initial load time: %0.2f seconds (%d%% overhead)'
        print msg % (measurements[0], initial_overhead)

