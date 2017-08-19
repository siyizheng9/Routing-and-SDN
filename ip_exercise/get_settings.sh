#! /bin/bash
listRouter="Funet Comnet Netlab Netcafe Aalto Kosh CSC Niksula"
listClient="client1 client2 client3"

for r in $listRouter; do
    echo "$r"
    sudo cp /var/lib/lxc/$r/rootfs/etc/quagga/ospfd.conf $r
done

# sudo cp /var/lib/lxc/$r/rootfs/etc/quagga/zebra.conf $r

