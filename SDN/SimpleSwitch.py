import json
from ryu.base import app_manager
from webob import Response
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, vlan
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from pprint import pprint

simple_switch_instance_name = 'simple_switch_api_app'
RULEID_PATTERN = r'[0-9]{1,4}|all'
DPID_PATTERN = r'[0-9a-f]{1,16}'


class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.switches = {}
        wsgi = kwargs['wsgi']
        wsgi.register(VlanController,
                      {simple_switch_instance_name: self})
        wsgi.register(FirewallController,
                      {simple_switch_instance_name: self})
        self.mac_to_port = {}
        self.BORDER_DPID_INNER_PORT = {1: [1, 2], 3: [1, 2],
                                       4: [1, 2], 6: [1, 2]}
        # self.vlan_to_port = {1: {1: -1, 2: -1, 3: -1, 4: -1},
        #                      2: {1: -1, 2: -1, 3: -1, 4: -1},
        #                      3: {1: -1, 2: -1, 3: -1, 4: -1},
        #                      4: {1: -1, 2: -1, 3: -1, 4: -1},
        #                      5: {1: -1, 2: -1, 3: -1, 4: -1},
        #                      6: {1: -1, 2: -1, 3: -1, 4: -1}}
        self.vlan_to_port = {}
        self.rule_table = {}  # {"dpid": {"ruleid": {}}}
        self.rule_list = {}  # {"ruleid": {...},...}
        self.ruleid = 1
        self.swdesc = {}  # {"s1": {"dpid":1, "s1-eth1": 1...}...}
        self.dpid_to_name = {}  # {"1": "s1"}
        self.port_to_name = {}  # {"1": {"1": "s1_eth1",...},...}

    def ofs_nbits(self, start, end):
        return (start << 6) + (end - start)

    def add_firewall_rule(self, dpid, entry):
        rule = entry.copy()
        action = entry.get('action')
        priority = entry.get('priority') + 100
        datapath = self.switches.get(dpid)
        entry.pop('name')
        entry.pop('description')
        entry.pop('priority')
        entry.pop('action')

        if datapath is not None:
            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto
            match = parser.OFPMatch(**entry)
            if action == 'accept':
                inst = [parser.OFPInstructionGotoTable(table_id=1)]
            else:
                inst = None
            mod = parser.OFPFlowMod(datapath=datapath, table_id=0,
                                    priority=priority, cookie=self.ruleid,
                                    match=match, instructions=inst,
                                    command=ofproto.OFPFC_ADD)
            datapath.send_msg(mod)
            self.rule_table[dpid] = {self.ruleid: rule}
            self.rule_list[self.ruleid] = rule
            self.ruleid = self.ruleid + 1
            print 'rule installed:'
            pprint(rule)
            return {'status': 'ok'}

    def del_firewall_rule(self, ruleid):
        dpid = None
        for switchid, rule in self.rule_table.items():
            if ruleid in rule:
                dpid = switchid
                self.rule_table[dpid].pop(ruleid)
                self.rule_list.pop(ruleid)
                break
        datapath = self.switches.get(dpid)
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        mod = parser.OFPFlowMod(datapath=datapath, table_id=0,
                                out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPG_ANY,
                                cookie=ruleid, cookie_mask=0xffff,
                                command=ofproto.OFPFC_DELETE)
        datapath.send_msg(mod)
        print 'rule deleted ruleid: %s' % ruleid
        return {'status': 'ok'}

    def set_vlan_to_port(self, dpid, entry):
        '''entry={'port': <port>, 'vid': <vid>}'''
        entry_port = entry['port']
        entry_vid = entry['vid']
        datapath = self.switches.get(dpid)

        if datapath is not None:
            if self.vlan_to_port[dpid][entry_port] != -1:
                return self.vlan_to_port
            if entry_port not in self.vlan_to_port[dpid]:
                return self.vlan_to_port

            # install flow to add vlan tag
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=entry_port)
            # eth_VLAN = ether.ETH_TYPE_8021Q
            # f = parser.OFPMatchField.make(
            #                 ofproto.OXM_OF_VLAN_VID, entry_vid)
            actions = [parser.OFPActionPushVlan(),
                       parser.OFPActionSetField(vlan_vid=(0x1000 | entry_vid))]
            inst = [parser.OFPInstructionGotoTable(table_id=2),
                    parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = parser.OFPFlowMod(datapath=datapath, table_id=1, priority=50,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)

            # install flow to remove vlan tag
            # match = parser.OFPMatch(reg0=entry_port, dl_vlan=entry_vid)
            match = parser.OFPMatch(reg0=entry_port,
                                    vlan_tci=(0x1000 | entry_vid))
            # match.set_vlan_vid(entry_vid)
            actions = [parser.OFPActionPopVlan(),
                       parser.OFPActionOutput(entry_port)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=50,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)
            self.vlan_to_port[dpid][entry_port] = entry_vid

            # install flow to drop packet with different vlan tag or
            # without vlan tag.
            match = parser.OFPMatch(reg0=entry_port)
            mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=49,
                                    cookie=1, match=match)
            datapath.send_msg(mod)
        return self.vlan_to_port

    def mod_port_vlan(self, dpid, entry):
        '''entry={'port': <port>, 'vid': <vid>}'''
        entry_port = entry['port']

        if self.vlan_to_port[dpid][entry_port] == -1:
            return self.vlan_to_port[dpid]
        else:
            # remove old flow entry
            self.del_vlan_to_port(dpid, entry)
            # add new flow entry
            self.set_vlan_to_port(dpid, entry)
            return self.vlan_to_port[dpid]

    def del_vlan_to_port(self, dpid, entry):
        '''entry={'port': <port>}'''
        entry_port = entry['port']
        datapath = self.switches.get(dpid)

        if self.vlan_to_port[dpid][entry_port] == -1:
            return self.vlan_to_port[dpid]
        else:
            # remove flow to add vlan tag
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=entry_port)
            mod = parser.OFPFlowMod(datapath=datapath, table_id=1,
                                    command=ofproto.OFPFC_DELETE,
                                    out_port=ofproto.OFPP_ANY,
                                    out_group=ofproto.OFPG_ANY,
                                    priority=50, match=match,)
            datapath.send_msg(mod)

            # remove flow to remove vlan tag
            entry_vid = self.vlan_to_port[dpid][entry_port]
            match = parser.OFPMatch(reg0=entry_port,
                                    vlan_tci=(0x1000 | entry_vid))
            mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=50,
                                    command=ofproto.OFPFC_DELETE,
                                    out_port=ofproto.OFPP_ANY,
                                    out_group=ofproto.OFPG_ANY,
                                    match=match)
            datapath.send_msg(mod)
            self.vlan_to_port[dpid][entry_port] = -1

            # remove flow of droping packet from different vlan
            match = parser.OFPMatch(reg0=entry_port)
            mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=49,
                                    cookie=1, cookie_mask=0xffff,
                                    command=ofproto.OFPFC_DELETE,
                                    out_port=ofproto.OFPP_ANY,
                                    out_group=ofproto.OFPG_ANY,
                                    match=match)
            datapath.send_msg(mod)
            return self.vlan_to_port[dpid]

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, CONFIG_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        ports = []
        for p in ev.msg.body:
            ports.append({'name': p.name, 'port_no': p.port_no})
        p = ports[0]
        self.swdesc[p['name']] = {'dpid': datapath.id}
        self.dpid_to_name[datapath.id] = p['name']
        sw = self.swdesc[p['name']]
        ports.pop(0)
        self.port_to_name[datapath.id] = {}
        self.vlan_to_port[datapath.id] = {}
        for p in ports:
            sw[p['name']] = p['port_no']
            self.vlan_to_port[datapath.id][p['port_no']] = -1
            self.port_to_name[datapath.id][p['port_no']] = p['name']
        # pprint(self.swdesc)
        # pprint(self.vlan_to_port)
        # pprint(self.dpid_to_name)
        # pprint(self.port_to_name)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_feature_handler(self, event):
        datapath = event.msg.datapath
        self.switches[datapath.id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.rule_table[datapath.id] = {}

        # install the table-miss flow entry in table 0.
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(table_id=1)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=0, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

        # install the table-miss flow entry in table 1.
        match = parser.OFPMatch()
        inst = [parser.OFPInstructionGotoTable(table_id=2)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=1, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

        # install the table-miss flow entry in table 2.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 2, 0, match, actions)

        # install the table-miss flow entry in table 3.
        match = parser.OFPMatch(reg0=1)
        actions = [parser.OFPActionOutput(1)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=1,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

        match = parser.OFPMatch(reg0=2)
        actions = [parser.OFPActionOutput(2)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=1,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

        match = parser.OFPMatch(reg0=3)
        actions = [parser.OFPActionOutput(3)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=1,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

        match = parser.OFPMatch(reg0=4)
        actions = [parser.OFPActionOutput(4)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=3, priority=1,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    def add_flow(self, datapath, table_id, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, table_id=table_id,
                                priority=priority, match=match,
                                instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, event):
        MULTIPATH = False
        msg = event.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        dpid = datapath.id  # dpid type 'int'
        self.mac_to_port.setdefault(dpid, {})

        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src
        vlan_pkt = pkt.get_protocol(vlan.vlan)

        in_port = msg.match['in_port']  # in_port type 'int'

        # print 'type dpid:%s in_port:%s' % (type(dpid), type(in_port))

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        self.mac_to_port[dpid].setdefault(src, set())
        self.mac_to_port[dpid][src].add(in_port)
        # TODO: send_group_mod()
        pprint(self.mac_to_port)

        if dst == 'ff:ff:ff:ff:ff:ff' and dpid in self.BORDER_DPID_INNER_PORT:
            print 'border datapath'
            out_ports = [1, 2, 3, 4]
            vlan_ports = []
            if vlan_pkt is not None:
                vid = vlan_pkt.vid
                print 'vid:%s' % vid
                for port, id in self.vlan_to_port[dpid].items():
                    if id == vid:
                        vlan_ports.append(port)
                    if id != -1:
                        out_ports.remove(port)
            if in_port == 3 or in_port == 4:
                if 3 in out_ports:
                    out_ports.remove(3)
                if 4 in out_ports:
                    out_ports.remove(4)
                actions = []
                # for p in out_ports:
                #     actions.append(parser.OFPActionOutput(p))
                # if vlan_pkt is not None:
                #     actions.append(parser.OFPActionPopVlan())
                # for p in vlan_ports:
                #     actions.append(parser.OFPActionOutput(p))
                # out = parser.OFPPacketOut(datapath=datapath,
                #                           buffer_id=ofproto.OFP_NO_BUFFER,
                #                           in_port=in_port, actions=actions,
                #                           data=msg.data)
                # datapath.send_msg(out)
                for p in out_ports+vlan_ports:
                    actions += [parser.NXActionRegLoad(
                        ofs_nbits=self.ofs_nbits(0, 15),
                        dst="reg0", value=p)]
                    actions += [parser.NXActionResubmitTable(
                        in_port=in_port, table_id=3)]
                    out = parser.OFPPacketOut(datapath=datapath,
                                              buffer_id=ofproto.OFP_NO_BUFFER,
                                              in_port=in_port, actions=actions,
                                              data=msg.data)
                    datapath.send_msg(out)
                    print 'port_out:%s' % p
                return
            else:
                if in_port in out_ports:
                    out_ports.remove(in_port)
                actions = []
                # for p in out_ports:
                #     actions.append(parser.OFPActionOutput(p))
                # if vlan_pkt is not None:
                #     actions.append(parser.OFPActionPopVlan())
                # for p in vlan_ports:
                #     actions.append(parser.OFPActionOutput(p))
                # out = parser.OFPPacketOut(datapath=datapath,
                #                           buffer_id=ofproto.OFP_NO_BUFFER,
                #                           in_port=in_port, actions=actions,
                #                           data=msg.data)
                for p in out_ports+vlan_ports:
                    actions += [parser.NXActionRegLoad(
                        ofs_nbits=self.ofs_nbits(0, 15),
                        dst="reg0", value=p)]
                    actions += [parser.NXActionResubmitTable(
                        in_port=in_port, table_id=3)]
                    out = parser.OFPPacketOut(datapath=datapath,
                                              buffer_id=ofproto.OFP_NO_BUFFER,
                                              in_port=in_port, actions=actions,
                                              data=msg.data)
                    datapath.send_msg(out)
                    print 'port_out:%s' % p
                datapath.send_msg(out)
                return

        if dst in self.mac_to_port[dpid]:
            l = list(self.mac_to_port[dpid][dst])
            out_port = l[0]
            if len(l) == 1:
                out_port = l[0]
            else:
                self.send_group_mod(datapath, l)
                MULTIPATH = True

        elif dst == 'ff:ff:ff:ff:ff:ff':
            print 'Flooding dpid:%s' % (dpid)
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(datapath=datapath,
                                      buffer_id=ofproto.OFP_NO_BUFFER,
                                      in_port=in_port, actions=actions,
                                      data=msg.data)
            datapath.send_msg(out)
        else:
            #  drop
            print 'cannot find correct port'
            return

        if MULTIPATH is False:
            # actions = [parser.OFPActionOutput(out_port)]
            actions = [parser.NXActionRegLoad(ofs_nbits=self.ofs_nbits(0, 15),
                                              dst="reg0",
                                              value=out_port)]

            if out_port != ofproto.OFPP_FLOOD:
                match = parser.OFPMatch(in_port=in_port,
                                        eth_dst=dst, eth_src=src)
                inst = [parser.OFPInstructionGotoTable(table_id=3),
                        parser.OFPInstructionActions(
                            ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(datapath=datapath, table_id=2,
                                        priority=1,
                                        match=match, instructions=inst)
                datapath.send_msg(mod)
                # actions = [parser.OFPActionOutput(out_port)]
                # actions = [parser.OFPAcionOutput(ofproto.OFPP_TABLE)]
                # in_port = ofproto.OFPP_CONTROLLER
                actions += [parser.NXActionResubmitTable(
                    in_port=in_port, table_id=3)]
                out = parser.OFPPacketOut(datapath=datapath,
                                          buffer_id=ofproto.OFP_NO_BUFFER,
                                          in_port=in_port, actions=actions,
                                          data=msg.data)
                datapath.send_msg(out)
                # self.add_flow(datapath, 2, 1, match, actions)
        else:
            actions = [parser.OFPActionGroup(group_id=datapath.id)]
            match = parser.OFPMatch(in_port=in_port,
                                    eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 2, 2, match, actions)

            out = parser.OFPPacketOut(datapath=datapath,
                                      buffer_id=ofproto.OFP_NO_BUFFER,
                                      in_port=in_port, actions=actions,
                                      data=msg.data)
            datapath.send_msg(out)

    def send_group_mod(self, datapath, out_ports):
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser

        group_id = datapath.id
        weight_1, weight_2 = 50, 50
        port_3, port_4 = out_ports
        # action_1 = [parser.OFPActionOutput(port_3)]
        # action_2 = [parser.OFPActionOutput(port_4)]
        actions_1 = [parser.NXActionRegLoad(ofs_nbits=self.ofs_nbits(0, 15),
                                            dst="reg0", value=port_3),
                     parser.NXActionResubmitTable(table_id=3)]
        actions_2 = [parser.NXActionRegLoad(ofs_nbits=self.ofs_nbits(0, 15),
                                            dst="reg0", value=port_4),
                     parser.NXActionResubmitTable(table_id=3)]

        watch_port = ofproto_v1_3.OFPP_ANY
        watch_group = ofproto_v1_3.OFPQ_ALL

        bucket = [parser.OFPBucket(weight_1, watch_port,
                                   watch_group, actions_1),
                  parser.OFPBucket(weight_2, watch_port,
                                   watch_group, actions_2)]

        req = parser.OFPGroupMod(datapath, ofp.OFPGC_ADD,
                                 ofp.OFPGT_SELECT, group_id, bucket)

        datapath.send_msg(req)


class VlanController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(VlanController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]

    @route('VlanPorts', '/task2/ports/', methods=['GET'])
    def list_vlan_table(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        dpid_to_name = simple_switch.dpid_to_name
        port_to_name = simple_switch.port_to_name
        vlan_table = simple_switch.vlan_to_port
        output = {}
        for dpid, port_vlan in vlan_table.items():
            output.setdefault(dpid_to_name[dpid], {})
            output[dpid_to_name[dpid]]['dpid'] = dpid
            for port, vlanNumber in port_vlan.items():
                output[dpid_to_name[dpid]][port_to_name[dpid][port]] = \
                        {'port_no': port, 'vlan': vlanNumber}
        # output = vlan_table
        body = json.dumps(output)
        return Response(content_type='application/json', body=body)

    @route('VlanPorts', '/task2/ports/{dpid}', methods=['POST'],
           requirements={'dpid': DPID_PATTERN})
    def put_vlan_table(self, req, **kwargs):
        '''POST -d {'port': <port>, 'vid': <vid>}'''
        # print "put_vlant_table"
        simple_switch = self.simple_switch_app
        kw = kwargs['dpid']
        kw = (dpid_lib._DPID_LEN - len(kw))*'0' + kw
        dpid = dpid_lib.str_to_dpid(kw)
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            # return Response(status=400)
            return Response('ValueError')

        if dpid not in simple_switch.vlan_to_port:
            return Response(status=404)

        try:
            vlan_table = simple_switch.set_vlan_to_port(dpid, new_entry)
            body = json.dumps(vlan_table[dpid])
            return Response(content_type='application/json', body=body)
        except Exception:
            return Response(status=500)

    @route('VlanPort', '/task2/port/{dpid}', methods=['GET'],
           requirements={'dpid': DPID_PATTERN})
    def get_vlan_table(self, req, **kwargs):
        '''GET '''
        simple_switch = self.simple_switch_app
        kw = kwargs['dpid']
        kw = (dpid_lib._DPID_LEN - len(kw))*'0' + kw
        dpid = dpid_lib.str_to_dpid(kw)

        if dpid not in simple_switch.vlan_to_port:
            return Response(status=404)

        vlan_table = simple_switch.vlan_to_port
        body = json.dumps(vlan_table[dpid])
        return Response(content_type='application/json', body=body)

    @route('VlanPort', '/task2/port/{dpid}', methods=['PUT'],
           requirements={'dpid': DPID_PATTERN})
    def mod_port_vlan(self, req, **kwargs):
        '''PUT -d {'port': <port>, 'vid': <vid>}'''
        simple_switch = self.simple_switch_app
        kw = kwargs['dpid']
        kw = (dpid_lib._DPID_LEN - len(kw))*'0' + kw
        dpid = dpid_lib.str_to_dpid(kw)
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            # return Response(status=400)
            return Response('ValueError')

        if dpid not in simple_switch.vlan_to_port:
            return Response(status=404)
        # TODO simple_switch.mod_port_vlan
        vlan_table = simple_switch.mod_port_vlan(dpid, new_entry)
        body = json.dumps(vlan_table)
        return Response(content_type='application/json', body=body)

    @route('VlanPort', '/task2/port/{dpid}', methods=['DELETE'],
           requirements={'dpid': DPID_PATTERN})
    def del_port_vlan(self, req, **kwargs):
        '''DELETE -d {'port': <port>}'''
        simple_switch = self.simple_switch_app
        kw = kwargs['dpid']
        kw = (dpid_lib._DPID_LEN - len(kw))*'0' + kw
        dpid = dpid_lib.str_to_dpid(kw)
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            # return Response(status=400)
            return Response('ValueError')

        if dpid not in simple_switch.vlan_to_port:
            return Response(status=404)
        # TODO simple_switch.del_port_vlan
        vlan_table = simple_switch.del_vlan_to_port(dpid, new_entry)
        body = json.dumps(vlan_table)
        return Response(content_type='application/json', body=body)


class FirewallController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(FirewallController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]
        self.arguments = ['name', 'description', 'priority', 'in_port',
                          'eth_src', 'eth_dst', 'eth_type', 'ipv4_src',
                          'ipv4_dst', 'ip_proto', 'tp_sport', 'tp_dport',
                          'action']

    @route('Firewall', '/task3/rules/', methods=['GET'])
    def list_rule_table(self, req, **kwargs):
        simple_switch = self.simple_switch_app
        rule_table = simple_switch.rule_table
        body = json.dumps(rule_table)
        return Response(content_type='application/json', body=body)

    @route('Firewall', '/task3/rules/{dpid}', methods=['POST'],
           requirements={'dpid': DPID_PATTERN})
    def add_firewall_rule(self, req, **kwargs):
        '''POST -d {"name":"example", "description":"nothing", "in_port": 1}'''
        simple_switch = self.simple_switch_app
        kw = kwargs['dpid']
        kw = (dpid_lib._DPID_LEN - len(kw))*'0' + kw
        dpid = dpid_lib.str_to_dpid(kw)
        try:
            new_entry = req.json if req.body else {}
        except ValueError:
            return Response('ValueError')

        if dpid not in simple_switch.rule_table:
            return Response(status=404)

        try:
            self.check_rule_error(new_entry)
        except Exception as inst:
            print inst
            return Response(inst.args[0])

        r = simple_switch.add_firewall_rule(dpid, new_entry)
        body = json.dumps(r)
        return Response(content_type='application/json', body=body)

    @route('Firewall', '/task3/rule/{ruleid}', methods=['GET'],
           requirements={'ruleid': RULEID_PATTERN})
    def get_firewall_rule(self, req, **kwargs):
        '''GET /task3/rule/<ruleid> '''
        ruleid = int(kwargs['ruleid'])
        simple_switch = self.simple_switch_app

        if ruleid not in simple_switch.rule_list:
            return Response(status=404)
        else:
            body = json.dumps(simple_switch.rule_list[ruleid])
            return Response(content_type='application/json', body=body)

    @route('Firewall', '/task3/rule/{ruleid}', methods=['DELETE'],
           requirements={'ruleid': RULEID_PATTERN})
    def del_firewall_rule(self, req, **kwargs):
        '''GET /task3/rule/<ruleid> '''
        ruleid = int(kwargs['ruleid'])
        simple_switch = self.simple_switch_app

        if ruleid not in simple_switch.rule_list:
            return Response(status=404)
        else:
            r = simple_switch.del_firewall_rule(ruleid)
            body = json.dumps(r)
            return Response(content_type='application/json', body=body)

    def check_rule_error(self, entry):
        for key, value in entry.items():
            if key not in self.arguments:
                raise Exception('invalid arguments:%s' % key)

        if entry.get('name') is None:
            raise Exception('name is required')

        if entry.get('description') is None:
            raise Exception('description is required')

        if entry.get('in_port') is None:
            raise Exception('in_port is required')

        if entry.get('action') is None:
            raise Exception('action is required')

        if entry.get('priority') is None:
            raise Exception('priority is required')

        if entry.get('eth_type') is not None:
            if entry.get('eth_type') != '0x8000':
                raise Exception('eth_type should be 0x8000')

        if entry.get('tp_sport') is not None or \
                entry.get('tp_dport') is not None:
                if entry.get('ip_proto') is None:
                    raise Exception('ip_proto is requied')
