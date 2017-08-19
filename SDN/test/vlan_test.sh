#!/bin/bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
curl -X POST -d '{"port": 1, "vid": 1}' http://localhost:8080/task2/ports/0000000000000001
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
curl -X PUT -d '{"port": 1, "vid": 2}' http://localhost:8080/task2/port/0000000000000001
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
curl -X DELETE -d '{"port": 1}' http://localhost:8080/task2/port/0000000000000001
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
