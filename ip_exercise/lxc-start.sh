#! /bin/bash

brctl addbr lxcbr1
brctl addbr lxcbr2
brctl addbr lxcbr3
brctl addbr lxcbr4
brctl addbr lxcbr5
brctl addbr lxcbr6
brctl addbr lxcbr7
brctl addbr lxcbr8
brctl addbr lxcbr9
brctl addbr lxcbr10
brctl addbr lxcbr11
brctl addbr lxcbr12

ifconfig lxcbr1 up
ifconfig lxcbr2 up
ifconfig lxcbr3 up
ifconfig lxcbr4 up
ifconfig lxcbr5 up
ifconfig lxcbr6 up
ifconfig lxcbr7 up
ifconfig lxcbr8 up
ifconfig lxcbr9 up
ifconfig lxcbr10 up
ifconfig lxcbr11 up
ifconfig lxcbr12 up

lxc-start -n Funet -d
lxc-start -n Comnet -d
lxc-start -n Netlab -d
lxc-start -n Netcafe -d
lxc-start -n client1 -d
lxc-start -n client2 -d
lxc-start -n client3 -d
lxc-start -n Aalto -d
lxc-start -n Kosh -d
lxc-start -n CSC -d
lxc-start -n Niksula -d

echo "All containers/Routers is now started!"
echo "Use 'lxc-ls --fancy' to view containers/routers"

