#!/bin/bash
curl http://localhost:8080/task3/rules/
curl -X POST -d '{"name": "test", "description": "test", "priority": 10, "in_port": 1, "action": "drop"}' http://localhost:8080/task3/rules/0000000000000001
curl -X POST -d '{"name": "test", "description": "test", "priority": 10, "in_port": 2, "action": "accept"}' http://localhost:8080/task3/rules/0000000000000001
curl http://localhost:8080/task3/rule/1
curl http://localhost:8080/task3/rule/2
curl -X DELETE http://localhost:8080/task3/rule/1
