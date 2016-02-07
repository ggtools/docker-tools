#!/usr/bin/env python3

__author__ = 'xtof'

import argparse
import re
import logging
import sys
from subprocess import Popen, PIPE
from docker import Client
from docker.utils import kwargs_from_env
from dns.resolver import Resolver
from dns.exception import DNSException

# Templates for nsupdate
zone_update_start_template = """server {0}
zone {1}.
"""

zone_update_template = """update delete {0}.{1}
update add {0}.{1} 60 A {2}
"""

zone_update_add_alias_template = """update delete {0}.{1}
update add {0}.{1} 600 CNAME {2}.{1}.
update add {2}.{1} 600 TXT dockerDDNS-alias:{0}:
"""

zone_update_delete_record_template = """update delete {0}.{1}
"""


def register_container(container_id):
    detail = c.inspect_container(container_id)
    container_hostname = detail["Config"]["Hostname"]
    container_name = detail["Name"].split('/', 1)[1]
    container_ip = detail["NetworkSettings"]["IPAddress"]
    logging.info("Updating %s to ip (%s|%s) -> %s", container_id, container_hostname, container_name, container_ip)
    if not args.dry_run:
        nsupdate = Popen(['nsupdate', '-k', args.key], stdin=PIPE)
        nsupdate.stdin.write(bytes(zone_update_start_template.format(args.server, args.zone), "UTF-8"))
        nsupdate.stdin.write(bytes(zone_update_template.format(container_hostname, args.domain, container_ip), "UTF-8"))
        if container_name != container_hostname:
            nsupdate.stdin.write(bytes(zone_update_add_alias_template.format(container_name, args.domain, container_hostname), "UTF-8"))
            if re.search("_", container_name):
                alternate_name = re.sub('_','-',container_name)
                logging.info("Adding alternate name %s to  %s", alternate_name, container_name)
                nsupdate.stdin.write(bytes(zone_update_add_alias_template.format(alternate_name, args.domain, container_hostname), "UTF-8"))
        nsupdate.stdin.write(bytes("send\n", "UTF-8"))
        nsupdate.stdin.close()


def remove_container(container_id):
    logging.info("Destroying %s", container_id)
    short_id = container_id[:12]
    record_to_delete = [short_id]
    logging.debug("Looking for alias to %s.%s", short_id, args.domain)

    try:
        answers = resolver.query("{0}.{1}.".format(short_id, args.domain), "TXT", raise_on_no_answer=False).rrset
        if answers:
            for answer in answers:
                logging.debug("Checking TXT record %s for alias", answer)
                match = re.search(r"dockerDDNS-alias:([^:]+):", answer.to_text())
                if match:
                    record_to_delete.append(match.group(1))
    except DNSException as e:
        logging.error("Cannot get TXT record for %s: %s", short_id, e)
    except:
        logging.error("Unexpected error: %s", sys.exc_info()[0])
        raise

    if not args.dry_run:
        nsupdate = Popen(['nsupdate', '-k', args.key], stdin=PIPE)
        nsupdate.stdin.write(bytes(zone_update_start_template.format(args.server, args.zone), "UTF-8"))

        for record in record_to_delete:
            logging.info("Removing record for %s", record)
            nsupdate.stdin.write(bytes(zone_update_delete_record_template.format(record, args.domain), "UTF-8"))

        nsupdate.stdin.write(bytes("send\n", "UTF-8"))
        nsupdate.stdin.close()


parser = argparse.ArgumentParser()

parser.add_argument("--key", required=True, help="Path to the dynamic dns key")
parser.add_argument("--server", help="IP/Hostname of the server to update", default="127.0.0.1")
parser.add_argument("--domain", help="The domain to be updated", required=True)
parser.add_argument("--zone", help="The zone to be updated (default to the domain)")

parser.add_argument("--dry-run", help="Run in dry run mode without doing any update", default=False, action="store_true")
parser.add_argument("--catchup", help="Register the running containers on startup", default=False, action="store_true")

parser.add_argument("--log-level", help="Log level to display", default="INFO")
parser.add_argument("--log-file", help="Where to put the logs", default="/var/log/docker-ddns.log")

args = parser.parse_args()

logging.basicConfig(level=getattr(logging,args.log_level.upper()),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename=(args.log_file if args.log_file != '-' else None))

if args.zone is None:
    args.zone = args.domain

logging.info("Starting with arguments %s", args)

c = Client(**(kwargs_from_env()))

resolver = Resolver()
resolver.nameservers = [args.server]

if args.catchup:
    logging.info("Registering existing containers")
    containers = c.containers()
    for container in containers:
        register_container(container["Id"])


# TODO use docker-py streaming API
events_pipe = Popen(['docker', 'events'], stdout=PIPE)

while True:
    line = events_pipe.stdout.readline()
    if line != '':
        text_line = line.decode().rstrip()
        logging.debug("Read line %s", text_line)
        m = re.search(r"\s+([0-9a-f]{64}):.*\s+([a-z]+)\s*$", text_line)
        if m:
            event = m.group(2)
            container_id = m.group(1)
            logging.debug("Got event %s for container %s", event, container_id)

            if event == "start":
                register_container(container_id)
            elif event == "destroy":
                remove_container(container_id)
    else:
        print("Done return code: ", events_pipe.returncode)
        break

# 2014-11-28T15:32:04.000000000+01:00 a3d66b00acc9adbdbdbc91cc664d2d94b6a07cc4295c5cf54fcc595e2aa92a43: (from mongo:latest) restart
# 2015-03-05T08:36:14.000000000+01:00 eb75c1a5ad836d008b0fd66bf6b1ea353510175e8caa619e59d9851029b1ceca: (from ggtools/zabbix-server:latest) exec_start: ifconfig eth0
