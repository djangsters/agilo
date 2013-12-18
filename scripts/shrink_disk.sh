#!/bin/sh

# root cleanup
dd if=/dev/zero of=/foo.zero
rm /foo.zero

# swap cleanup
swapoff -a
dd if=/dev/zero of=/dev/sdb1
mkswap -L agilovm-swap /dev/sdb1
