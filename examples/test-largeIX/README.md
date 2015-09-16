# Testing

## Generate configs/policies

```bash
$ cd  ~/sdx-parallel/examples/test-amsix/
$ python generate_configs.py
```

## Initialize RIBs for the participants
```bash
$ cd  ~/sdx-parallel/pctrl
$ python initialize_ribs.py
```

## Start the Pctrl
```bash
$ cd  ~/sdx-parallel/pctrl
$ python participant_controller.py test-amsix <id>
```

## FLANC - Reference Monitor Logger

This script saves every flowmod with a timestamp to the specified file (e.g. test.log)

```bash
$ cd ~/sdx-parallel/flanc
$ ./reflog.py localhost 5555 sdx <path of log file>
```

## xbgp - ExaBGP Simulator

This module reads bgp updates from a bgp dump file and sends them in ExaBGP format to xrs

### Run xbgp

```bash
$ cd ~/sdx-parallel/xbgp
$ ./xbgp.py localhost 6000 xrs <path of bgp updates file>
```

### Run xrs

```bash
$ cd ~/sdx-parallel/xrs
$ python route_server.py <name of example>
```


## FLANC - Reference Monitor Log Replay

### Run RefMon

After logging all the flow mods, the flow mods can be replayed using LogClient.

```bash
$ ryu-manager ~/sdx-ryu/flanc/refmon.py --refmon-config <path of config file>
```

### Run LogClient

```bash
$ ./log_client.py localhost 5555 sdx <path of input file>
```
