#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

class Exercise1Topo( Topo ):
    """Custom topology for exercise 1 of SDN routing

   Three switches plus a switch connecting them and two hosts for each of the three first switches:

   host --- switch --- switch --- switch --- host
       host --|          |           |-- host
       host --|          |
                         |
              host --- switch --- host

    """
    def __init__( self ):

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        A1 = self.addHost( '1a' )
        A2 = self.addHost( '1b' )
        B1 = self.addHost( '6a' )
        B2 = self.addHost( '6b' )
        C1 = self.addHost( '3a' )
        C2 = self.addHost( '3b' )
        D1 = self.addHost( '4a' )
	D2 = self.addHost( '4b' )
        ASwitch = self.addSwitch( 's1' )
        BSwitch = self.addSwitch( 's6' )
        CSwitch = self.addSwitch( 's3' )
        DSwitch = self.addSwitch( 's4' )
        ESwitch = self.addSwitch( 's5' )
        FSwitch = self.addSwitch( 's2' )

        # Add links
        self.addLink( A1, ASwitch )
        self.addLink( A2, ASwitch )
        self.addLink( B1, BSwitch )
        self.addLink( B2, BSwitch )
        self.addLink( C1, CSwitch )
        self.addLink( C2, CSwitch )
        self.addLink( D1, DSwitch )
        self.addLink( D2, DSwitch )
        self.addLink( ASwitch, ESwitch )
        self.addLink( ASwitch, FSwitch )
        self.addLink( BSwitch, ESwitch )
        self.addLink( BSwitch, FSwitch )
        self.addLink( CSwitch, ESwitch )
        self.addLink( CSwitch, FSwitch )
        self.addLink( DSwitch, ESwitch )
        self.addLink( DSwitch, FSwitch )


def runExercise1():
    "Create network and run simple performance test"
    topo = Exercise1Topo()
    net = Mininet(topo=topo,controller=RemoteController)
    net.start()
    net.get('1a').setIP('192.168.0.10/24')
    net.get('1a').setMAC('00:00:00:00:00:1A')
    net.get('1b').setIP('192.168.0.11/24')
    net.get('1b').setMAC('00:00:00:00:00:1B')
    net.get('6a').setIP('192.168.0.60/24')
    net.get('6a').setMAC('00:00:00:00:00:6A')
    net.get('6b').setIP('192.168.0.61/24')
    net.get('6b').setMAC('00:00:00:00:00:6B')
    net.get('3a').setIP('192.168.0.30/24')
    net.get('3a').setMAC('00:00:00:00:00:3A')
    net.get('3b').setIP('192.168.0.31/24')
    net.get('3b').setMAC('00:00:00:00:00:3B')
    net.get('4a').setIP('192.168.0.40/24')
    net.get('4a').setMAC('00:00:00:00:00:4A')
    net.get('4b').setIP('192.168.0.41/24')
    net.get('4b').setMAC('00:00:00:00:00:4B')
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
#    net.pingAll()
    cli = CLI(net)
#    net.interact()
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    runExercise1()
