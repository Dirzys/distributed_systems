====================
Distributed Systems Coursework 2014 Fall
====================

Coursework requirements and description:

http://www.inf.ed.ac.uk/teaching/courses/ds/assignment1415/DSAssignment/DSAssignment.pdf

====================
Run the code
====================
To run the code run 

./run.sh input.txt 

from main directory. It will create log.txt file with
logged output in it for both MST and Broadcasts tasks. Code is written in Python.

The code consists of 5 main files:
1. main.py – the main file that calls file parser, MST finder and for each of broadcasts
performs a broadcast.
2. fileParser.py – parses the input file and initializes a Node object for each of the provided
nodes.
3. logProducer.py – logs the required information into the output file (log.txt)
4. MST.py includes all the required functions to run MST, functions as a base station.
5. Node.py includes the Node object that can perform all necessary operations as a node.

======================
Description
======================

I was using a separate thread for each of the nodes, so they can actually perform
synchronously. When searching for MST, the base station (or the code in MST.py file) is
responsible for alerting all nodes to discover their neighbours first and since nodes does not
know their neighbours yet the discover message broadcast is simulated in the following way:
node puts a discover message into the events_queue (the queue of messages maintained by
base station) and then base station routes this message to all the neighbours of the node
within the distance 10 (puts the discover message into the neighbour node’s message queue –
the queue of arrived messages maintained by the specific node). Base station then alerts all
nodes to send discover responses to all requesters and from this point nodes start sharing the
information between each other without a help from base station – they just put a message
into the message queue of the receiving node. Base station now can only alert nodes to start
searching for a new edge to be added within a connected component and alert them to start
merging. Since I am using thread for each of the nodes there was a complication to terminate
threads since they are all just waiting for a message if no one is sending any. In such case,
base station handles this termination by sending ‘beacon’ message to nodes if all nodes are
sitting idle for 20 check rounds.

Nodes find MST as described in SynchGHS algorithm. To communicate with neighbours
node sends ‘neighbour’ message by adding this message to neighbours message queue. To
broadcast a link decision or id proposal I used flooding method. Then flooding, same
message is not sent back to the sender so nodes do not need to worry about same messages. It
is important to note that each node only stores the part of MST that includes links of this
node or links between two neighbours of this node. The reason why it stores links between
neighbours is that it is then easier for the node to find a new link that can be added into MST
(if there is still a neighbour that is not yet in MST it means the link to this neighbour can still
be considered for addition)

In part 2, I executed broadcasts in order as required. For each broadcast base station first
alerts all nodes to start a broadcast (if node is not the initiator then it just waits for the sensor
data to arrive). I have used very simple strategy – send sensor data message to the neighbour
with which the node has a link in MST (except the node that sent this message). If after
flooding the message to all nodes as described above the energy level drops below the
minimum budget – mark the node as not alive. Since this dead node has already received
sensor data, it will not receive any more during this broadcast task and can be left as dead
until the next broadcast. Before starting another broadcast base station checks if any of the
nodes is dead and if that is the case it will clean all the nodes and perform a new MST search
within the same network excluding the dead nodes. Base station then alerts alive nodes to
start next broadcast.