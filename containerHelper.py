#!/usr/bin/env python

__author__ = 'Christophe Labouisse'

import argparse
import re
import os

from docker import Client
from docker.utils import kwargs_from_env


def display_cpu(args):
    detail = c.inspect_container(args.container)
    if bool(detail["State"]["Running"]):
        container_id = detail['Id']
        cpu_usage = {}
        with open('/sys/fs/cgroup/cpuacct/docker/' + container_id + '/cpuacct.stat', 'r') as f:
            for line in f:
                m = re.search(r"(system|user)\s+(\d+)", line)
                if m:
                    cpu_usage[m.group(1)] = int(m.group(2))
        if args.type == "all":
            cpu = cpu_usage["system"] + cpu_usage["user"]
        else:
            cpu = cpu_usage[args.type]
        user_ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        print(float(cpu) / user_ticks)
    else:
        print(0)


def display_ip(args):
    detail = c.inspect_container(args.container)
    print(detail['NetworkSettings']['IPAddress'])


def display_memory(args):
    detail = c.inspect_container(args.container)
    if bool(detail["State"]["Running"]):
        container_id = detail['Id']
        with open('/sys/fs/cgroup/memory/docker/' + container_id + '/memory.stat', 'r') as f:
            for line in f:
                m = re.search(r"total_rss\s+(\d+)", line)
                if m:
                    print(m.group(1))
                    return

    print(0)


def display_network(args):
    detail = c.inspect_container(args.container)
    if bool(detail["State"]["Running"]):
        ifconfig = c.execute(args.container, "ifconfig eth0")
        m = re.search(("RX" if args.direction == "in" else "TX") + r" bytes:(\d+)", str(ifconfig))
        if m:
            print(m.group(1))
        else:
            b = c.execute(args.container, "cat /sys/devices/virtual/net/eth0/statistics/"+("rx" if args.direction == "in" else "tx")+"_bytes")
            if re.match(r"\s*\d+\s*", b):
                print(b)
            else:
                print(0)
    else:
        print(0)


def display_status(args):
    detail = c.inspect_container(args.container)
    state = detail["State"]
    if bool(state["Paused"]):
        print(1) # Paused
    elif bool(state["Running"]):
        print(0) # Running
    elif int(state["ExitCode"]) == 0:
        print(2) # Stopped
    else:
        print(3) # Crashed


parser = argparse.ArgumentParser()

parser.add_argument("container", help="Container name")

subparsers = parser.add_subparsers(title="Counters", description="Available counters", dest="dataType")

cpu_parser = subparsers.add_parser("cpu", help="Display CPU usage")
cpu_parser.add_argument("type", choices=["system", "user", "all"])
cpu_parser.set_defaults(func=display_cpu)

ip_parser = subparsers.add_parser("ip", help="Display IP Address")
ip_parser.set_defaults(func=display_ip)

memory_parser = subparsers.add_parser("memory", help="Display memory usage")
memory_parser.set_defaults(func=display_memory)

network_parser = subparsers.add_parser("network", help="Display network usage")
network_parser.add_argument("direction", choices=["in", "out"])
network_parser.set_defaults(func=display_network)

status_parser = subparsers.add_parser("status", help="Display the container status")
status_parser.set_defaults(func=display_status)

c = Client(**(kwargs_from_env()))

args = parser.parse_args()
args.func(args)
