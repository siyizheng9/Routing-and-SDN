#! /bin/bash

lxc-stop -n Funet
lxc-stop -n Comnet
lxc-stop -n Netlab
lxc-stop -n Netcafe
lxc-stop -n Aalto
lxc-stop -n Kosh
lxc-stop -n CSC
lxc-stop -n Niksula
lxc-stop -n client1
lxc-stop -n client2
lxc-stop -n client3


ifconfig lxcbr1 down
ifconfig lxcbr2 down
ifconfig lxcbr3 down
ifconfig lxcbr4 down
ifconfig lxcbr5 down
ifconfig lxcbr6 down
ifconfig lxcbr7 down
ifconfig lxcbr8 down
ifconfig lxcbr9 down
ifconfig lxcbr10 down
ifconfig lxcbr11 down
ifconfig lxcbr12 down

brctl delbr lxcbr1
brctl delbr lxcbr2
brctl delbr lxcbr3
brctl delbr lxcbr4
brctl delbr lxcbr5
brctl delbr lxcbr6
brctl delbr lxcbr7
brctl delbr lxcbr8
brctl delbr lxcbr9
brctl delbr lxcbr10
brctl delbr lxcbr11
brctl delbr lxcbr12

echo "All containers stopped"

echo "view containers status using 'lxc-ls --fancy'"
