#! /bin/bash
listRouter="Funet Comnet Netlab Netcafe Aalto Kosh CSC Niksula"
listClient="client1 client2 client3"

echo "starting rip and static routing"
echo "CSC"
sudo lxc-attach -n CSC -- /etc/init.d/ripd start
echo "Niksula"
sudo lxc-attach -n Niksula -- /etc/init.d/ripd start
echo "Kosh"
sudo lxc-attach -n Kosh -- /etc/init.d/ripd start
echo "Aalto"
sudo lxc-attach -n Aalto -- /etc/init.d/ripd start

echo "Funet"
sudo lxc-attach -n Funet -- service quagga start
# sudo cp Funet/zebra.conf_static /var/lib/lxc/Funet/rootfs/etc/quagga/zebra.conf_static
# sudo lxc-attach -n Funet -- chown quagga:quagga /etc/quagga/zebra.conf_static

echo "Comnet"
sudo lxc-attach -n Comnet -- /etc/init.d/zebra start
echo "Netlab"
sudo lxc-attach -n Netlab -- /etc/init.d/zebra start
echo "Netcafe"
sudo lxc-attach -n Netcafe -- /etc/init.d/zebra start
