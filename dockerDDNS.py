#!/usr/bin/env python3

__author__ = 'xtof'

import argparse
import re
import logging
from subprocess import Popen, PIPE
from docker import Client
from docker.utils import kwargs_from_env

parser = argparse.ArgumentParser()

parser.add_argument("--key", required=True, help="Path to the dynamic dns key")
parser.add_argument("--server", help="IP/Hostname of the server to update", default="127.0.0.1")
parser.add_argument("--domain", help="The domain to be updated", required=True)
parser.add_argument("--zone", help="The zone to be updated (default to the domain)")
parser.add_argument("--log-level", help="Log level to display", default="INFO")

args = parser.parse_args()

logging.basicConfig(level=getattr(logging,args.log_level.upper()))

if args.zone is None:
    args.zone = args.domain

c = Client(**(kwargs_from_env()))

# Too bad docker-py does not currently support docker events
p = Popen(['docker', 'events'], stdout=PIPE)

zone_update_template = """server {0}
zone {1}.
update delete {2}.{3}
update add {2}.{3} 60 A {4}
"""
zone_update_add_alias_template = """update delete {0}.{1}
update add {0}.{1} 600 CNAME {2}.{1}.
"""


while True:
    line = p.stdout.readline()
    if line != '':
        text_line = line.decode().rstrip()
        logging.debug("Read line %s", text_line)
        m = re.search(r"\s+([0-9a-f]{64}):.*\s+([a-z]+)\s*$", text_line)
        if m:
            event = m.group(2)
            container_id = m.group(1)
            logging.info("Got event %s for container %s", event, container_id)
            if event == "start":
                logging.info("Starting %s", container_id)
                detail = c.inspect_container(container_id)
                container_hostname = detail["Config"]["Hostname"]
                container_name = detail["Name"].split('/',1)[1]
                container_ip = detail["NetworkSettings"]["IPAddress"]
                nsupdate = Popen(['nsupdate', '-k', args.key], stdin=PIPE)
                nsupdate.stdin.write(bytes(zone_update_template.format(args.server, args.zone, container_hostname, args.domain, container_ip), "UTF-8"))
                if container_name != container_hostname:
                    nsupdate.stdin.write(bytes(zone_update_add_alias_template.format(container_name, args.domain, container_hostname), "UTF-8"))
                nsupdate.stdin.write(bytes("send\n", "UTF-8"))
                nsupdate.stdin.close()
        elif event == "destroy":
                logging.info("Destroying %s", container_id)
        else:
            logging.warning("Couldn't match RE in line %s", text_line)
    else:
        print("Done return code: ", p.returncode)
        break

# 2014-11-28T15:32:04.000000000+01:00 a3d66b00acc9adbdbdbc91cc664d2d94b6a07cc4295c5cf54fcc595e2aa92a43: (from mongo:latest) restart
