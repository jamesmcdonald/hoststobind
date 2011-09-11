#!/usr/bin/env python

# hoststobind - read a hosts file and write BIND zone files to the current directory
#
# Copyright (C) 2011 James McDonald <james@jamesmcdonald.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This is not very clever - junk in the hosts file will generate junk output
# I wrote it on a plane to solve a specific issue
# It explicitly ignores IPv6 entries (anything with a :)

import sys

forward = {}
reverse = {}

if len(sys.argv) < 2:
    print "Usage: %s <hostsfile>" % sys.argv[0]
    exit(1)
    
hosts = open(sys.argv[1], "rb")
for line in hosts:
    # Skip local, IPv6 and comments
    if 'localhost' in line or ':' in line or line.startswith('#'): continue
    cooked = line.strip().split()
    if len(cooked) == 0:
        continue
    
    # Set reverse to first name on line
    ip = [int(x) for x in cooked[0].split('.')]
    network = "%d.%d.%d.in-addr.arpa" % (ip[2],ip[1],ip[0])
    if network not in reverse:
        reverse[network] = {}
        print "Added reverse %s" % network
    reverse[network][ip[3]] = cooked[1]

    # Add a forward to the IP for each host
    for host in cooked[1:]:
        # Skip bare names
        if '.' not in host: continue
        (hostname, domainname) = host.split('.',1)
        if domainname not in forward:
            forward[domainname] = {}
            print "Added forward %s" % domainname
        forward[domainname][hostname] = cooked[0]

# A generic SOA with 5 minute TTL. This will need to be edited for real Internet use.
ZONEHEADER = """$TTL 300
$ORIGIN %s.
@\t\tIN\tSOA\t @ root (
\t\t\t\t42\t; serial
\t\t\t\t3H\t; refresh
\t\t\t\t15M\t; retry
\t\t\t\t1W\t; expiry
\t\t\t\t1D\t; minumum ttl
)

"""

z = open("named.zones", "w")

for network in reverse:
    w = open(network, "w")
    w.write(ZONEHEADER % (network))
    for host in sorted(reverse[network]):
        w.write("%d\t\tIN\tPTR\t%s.\n" % (host, reverse[network][host]))
    w.close()
    z.write("zone \"%s\" { type master; file \"%s\"; };\n" % (network, network));

for domain in forward:
    w = open(domain, "w")
    w.write(ZONEHEADER % (domain))
    # This does a pretty stupid string-based sort by address. Better than nothing.
    for entry in sorted(forward[domain].items(), lambda x,y: -1 if x[1]<y[1] else 1):
        # Use a 32 character hostname field. If your have silly hostnames, your output may suck.
        w.write("%-31s IN\tA\t%s\n" % (entry[0], entry[1]))
    w.close()
    z.write("zone \"%s\" { type master; file \"%s\"; };\n" % (domain, domain));

z.close()
