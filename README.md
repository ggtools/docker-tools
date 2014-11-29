# Simple Monitoring Tools for Docker

A set of scripts I use on a server with a Docker instance. All monitoring scripts are used with [Zabbix](http://www.zabbix.org).

## containerCount.sh

Very simple shell script to count the number of containers on the docker instance.

### Usage

    containerCount.sh (all|running|crashed)

Print the number of containers on the Docker instance.


## containerHelpery.py

A script inspired from [a nice article](http://blog.docker.com/2013/10/gathering-lxc-docker-containers-metrics/) about metric. It enables you to get several metrics from a running container:

- the user or system cpu used by the container
- the memory used by the container
- the ip address of the container
- the container status: running, stopped, crashed or paused
- the container's network activity

### Usage

    containerHelper.py [-h] container {cpu,ip,memory,network,status} ...

    positional arguments:
      container             Container name

    optional arguments:
      -h, --help            show this help message and exit

    Counters:
      Available counters

      {cpu,ip,memory,network,status}
        cpu                 Display CPU usage
        ip                  Display IP Address
        memory              Display memory usage
        network             Display network usage
        status              Display the container status

Additional information may be required depending on the counter prameter.

## dockerDDNS.py

A daemon to update a dynamic DNS when Docker starts containers. Designed to be used with bind9. Have a look at [this page](https://www.erianna.com/nsupdate-dynamic-dns-updates-with-bind9) to setup correctly your DNS before using it.

### Usage

    dockerDDNS.py [-h] --key KEY [--server SERVER] --domain DOMAIN
                         [--zone ZONE] [--log-level LOG_LEVEL]
                         [--log-file LOG_FILE]

    optional arguments:
      -h, --help            show this help message and exit
      --key KEY             Path to the dynamic dns key
      --server SERVER       IP/Hostname of the server to update
      --domain DOMAIN       The domain to be updated
      --zone ZONE           The zone to be updated (default to the domain)
      --log-level LOG_LEVEL
                            Log level to display
      --log-file LOG_FILE   Where to put the logs

### Installation

This script is designed to run as a daemon after Docker's startup. You'll find in the `upstart` directory a configuration file to have it launched on boot.

