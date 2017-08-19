#! /bin/bash
listRouter="Funet Comnet Netlab Netcafe Aalto Kosh CSC Niksula"
listClient="client1 client2 client3"

# /etc/init.d/zebra stop

echo "starting bgp routing"
echo "CSC"
sudo lxc-attach -n CSC -- /etc/init.d/zebra stop
sudo lxc-attach -n CSC -- /etc/init.d/ospfd start
echo "Niksula"
sudo lxc-attach -n Niksula -- /etc/init.d/zebra stop
sudo lxc-attach -n Niksula -- /etc/init.d/ospfd start
echo "Kosh"
sudo lxc-attach -n Kosh -- /etc/init.d/zebra stop
sudo lxc-attach -n Kosh -- /etc/init.d/ospfd start
echo "Aalto"
sudo lxc-attach -n Aalto -- /etc/init.d/zebra stop
sudo cp Aalto/ospfd.conf_bgp /var/lib/lxc/Aalto/rootfs/etc/quagga/ospfd.conf
sudo lxc-attach -n Aalto -- /etc/init.d/ospfd start
sudo lxc-attach -n Aalto -- /etc/init.d/bgpd start

echo "Funet"
sudo lxc-attach -n Funet -- service quagga stop
sudo cp Funet/zebra.conf /var/lib/lxc/Funet/rootfs/etc/quagga/zebra.conf
sudo cp Funet/daemons_bgp /var/lib/lxc/Funet/rootfs/etc/quagga/daemons
# sudo lxc-attach -n Funet -- chown quagga:quagga /etc/quagga/zebra.conf
sudo lxc-attach -n Funet -- service quagga start

echo "Comnet"
sudo lxc-attach -n Comnet -- /etc/init.d/zebra stop
sudo cp Comnet/zebra.conf /var/lib/lxc/Comnet/rootfs/etc/quagga/zebra.conf
sudo cp Comnet/ospfd.conf_bgp /var/lib/lxc/Comnet/rootfs/etc/quagga/ospfd.conf
sudo lxc-attach -n Comnet -- /etc/init.d/ospfd start
sudo lxc-attach -n Comnet -- /etc/init.d/bgpd start
echo "Netlab"
sudo lxc-attach -n Netlab -- /etc/init.d/zebra stop
sudo cp Netlab/zebra.conf /var/lib/lxc/Netlab/rootfs/etc/quagga/zebra.conf
sudo lxc-attach -n Netlab -- /etc/init.d/ospfd start
echo "Netcafe"
sudo lxc-attach -n Netcafe -- /etc/init.d/zebra stop
sudo cp Netcafe/zebra.conf /var/lib/lxc/Netcafe/rootfs/etc/quagga/zebra.conf
sudo lxc-attach -n Netcafe -- /etc/init.d/ospfd start
