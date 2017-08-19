# Prequisites
- update ryu to 4.8.1 or above

     `sudo pip uninstall ryu`
     
     `sudo pip install ryu`


- disable ipv6
  
  If you wish to disable IPv6 permanently in your VM

  edit the following line in `/etc/default/grub`:
  
  
  GRUB_CMDLINE_LINUX_DEFAULT="ipv6.disable=1 text"

   then run `sudo update-grub` and reboot


- assignment topo
  assignment topo `mininet/exercise1.py`


# Run app
`ryu-manager --verbose SimpleSwitch.py`

# REST API
### task2

- show the vlan configuration

   `curl http://localhost:8080/task2/ports/`
- add a VLAN to a port
 
    `curl -X POST -d '{"port": 1, "vid": 1}' http://localhost:8080/task2/ports/0000000000000001`

- modify the configuration of the port

   `curl -X PUT -d '{"port": 1, "vid": 2}' http://localhost:8080/task2/port/0000000000000001`
- delete a port and its configuration

  `curl -X DELETE -d '{"port": 1}' http://localhost:8080/task2/port/0000000000000001`

### task3
- list of rules applied in the VM ports

  `curl http://127.0.0.1:8080/task3/rules/`
- add a firewall rule to a port

    `curl -X POST -d '{"name": "test", "description": "test", "priority": 10, "in_port": 1, "action": "drop"}' http://localhost:8080/task3/rules/0000000000000001`

- delete the rule

   `curl -X DELETE http://localhost:8080/task3/rule/1`
