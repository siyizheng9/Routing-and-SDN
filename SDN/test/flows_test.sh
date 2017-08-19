ovs-ofctl del-flows s1
ovs-ofctl add-flow s1 "table=1 priority=0 actions=learn(table=1, priority=1, hard_timeout=30, NXM_OF_ETH_DST[]=NXM_OF_ETH_SRC[], output:NXM_OF_IN_PORT[] mod_vlan_vid:1), resubmit(,2)"
ovs-ofctl add-flow s1 "table=2 priority=0  actions=strip_vlan, FLOOD"
ovs-ofctl add-flow s1 "table=0 priority=10 in_port=1 actions=mod_vlan_vid:1, resubmit(,1)"
ovs-ofctl add-flow s1 "table=0 priority=10 in_port=2 actions=mod_vlan_vid:1, resubmit(,1)"

