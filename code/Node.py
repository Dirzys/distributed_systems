from logProducer import get_file_name, get_file_mode
import math
import logging
import Queue

logging.basicConfig(level=logging.INFO,
                    format='%(message)s',
                    filename=get_file_name(),
                    filemode=get_file_mode())


class Node:
    """ Class for all nodes """
    message_queue = {}
    minimum_budget = 0

    def __init__(self, node_id, position, energy):
        """
        Create new node by passing the following information.
        :param node_id: Unique ID of the node
        :param position: Position of the node in form (x, y) coordinate
        :param energy: The current energy of the node

        The node then also initializes and maintains the following information:
            - Is this node a leader (initially yes)
            - Is this node elected as being a leader (initially no)
            - Is this node alive (initially yes)
            - The list of all the neighbors for the node
            - The currently known MST for node (note that node keeps only the links that are connected between
                this node and other node or between two nodes that are both neighbors of this node
            - Message queue. This is the queue there all the messages from other nodes or base station comes.
        """
        self.node_id = int(node_id)
        self.position = (float(position[0]), float(position[1]))
        self.energy = float(energy)
        self.leader = True
        self.elected = False
        self.alive = True
        self.neighbors = []
        self.mst = []
        self.message_queue[self.node_id] = Queue.Queue()

    def discover(self, events_queue):
        """
        Node broadcasts a discover message. Since node does not yet know to which nodes he is sending the message
        base station simulates the routing of these messages by maintaining an events queue.
        :param events_queue: Base station maintained queue.
        """
        events_queue.put(('discover', self.node_id, self.position))

    def discover_response(self):
        """
        Respond to discover (by sending discover response) and discover response
        (by updating the neighbors) messages. If message from base station is received - stop waiting and terminate.
        """
        while True:
            if self.message_queue[self.node_id].empty():
                continue
            message_type, sender_id, sender_position = self.message_queue[self.node_id].get()
            if message_type == 'beacon':
                break
            if message_type == 'discover':
                self.message_queue[sender_id].put(('discover_response', self.node_id, self.position))
            if message_type == 'discover_response':
                self.update_neighbors(sender_id, sender_position)

    def update_neighbors(self, responding_node_id, responding_node_position):
        """
        Update the list of neighbors by adding a new neighbor.
        :param responding_node_id: ID of neighbor node to be added
        :param responding_node_position: Position of neigbor node to be added
        """
        self.neighbors.append((responding_node_id, responding_node_position))

    def send_neighbor(self, message_id, message, neighbor_id):
        """
        Send a message to neighbor. This is simulated by adding the message into neighbors message queue.
        :param message_id: Message id, typically equals to the current level
        :param message: Message that needs to be sent
        :param neighbor_id: Node ID to which message need to be sent
        """
        self.message_queue[neighbor_id].put(('neighbor', message_id, message, self.node_id))

    def is_neighbor(self, node_id):
        """
        Finds whether node is a neighbor or not.
        :param node_id: ID of the node to be checked
        :return: Boolean variable saying if node is a neighbor or not
        """
        for neighbor, _ in self.neighbors:
            if neighbor == node_id:
                return True
        return False

    def get_links_in_mst_from_me(self):
        """
        Get the number of links from this node in the current MST.
        Note that node keeps links in a way such that if this node is in the link, then it is presented first
        """
        return len([node_one for node_one, _ in self.mst if node_one == self.node_id])

    def find_cheapest_link(self):
        """
        Find the minimum distance and the associated node amongst
        all this node's neighbors that are not already in mst
        :return: Cheapest link and distance to the node on the other end of the link.
            Return None if no more links can be added from this node
        """
        all_distances = ([(self.find_distance(neighbor_position), (self.node_id, neighbor_id))
                          for neighbor_id, neighbor_position in self.neighbors
                          if not [neighbor_id for link in self.mst if neighbor_id in link]])
        return min(all_distances) if all_distances else None

    def choose_best_link(self, level, events_queue):
        """
        Main function that chooses the best/cheapest link within a connected component
        and updates MST with a newly found best link.
        :param level: The current level of MST algorithm.
        :param events_queue: Used only for logging the cheapest link.
        """
        # If a leader, broadcast a message inside the tree for each node to identify a new edge to add to MST.
        if self.leader:
            self.flood_tree(level, message={'type': 'find_cheapest_link'})
        # Wait for the messages or answers to messages
        cheapest_link = self.receive_cheapest_link(level)
        # Append this neighbor to MST if a leader and if cheapest link is found
        if self.leader and cheapest_link:
            events_queue.put(('log', cheapest_link[1]))
            self.add_link_to_mst(cheapest_link[1])
            # Finally, flood the decision to the tree
            self.flood_tree(level, message={'type': 'link_decision', 'data': cheapest_link[1]})
        # Wait for the link decision to arrive
        self.receive_neighbor(level)

    def merge(self, level):
        """
        Main function used to merge connected components by electing a new leader within each new component.
        :param level: The current level of MST algorithm
        """
        # At the start of the merge none of the nodes are elected
        self.elected = False
        # If a leader, propose id by flooding leader id to the tree
        if self.leader:
            self.flood_tree(level, message={'type': 'id_proposal', 'data': self.node_id})
        # Wait for receiving messages
        self.receive_neighbor(level)

    def flood_tree(self, message_id=None, message=None, except_nodes=None):
        """
        Send neighbor messages to all neighbors that are already in MST and has a link to this node.
        In case node shares the link decision with the node from other connected component (this can only happen
            then the cheapest link is actually the link between these two nodes in different components) - send full
            currently known MST, so that nodes in other components knows about the nodes and MST in this one.
        In case data broadcast needs to be performed (large volume data to be sent) - update the energy and log
            the data transfer.
        If after performing all broadcast energy level drops below minimum budget - node dies.
        :param message_id: The ID of the message to be sent
        :param message: The message to be sent
        :param except_nodes: The list of node IDs to which the message should not be sent
        """
        for link in self.mst:
            if (link[0] == self.node_id) and (not link[1] in (except_nodes if except_nodes else [])):
                if (message['type'] == 'link_decision') and (self.node_id in message['data']) and (link[1] in message['data']):
                    self.send_neighbor(message_id, {'type': 'my_current_mst', 'data': self.mst}, link[1])
                    continue
                if message['type'] == 'data_broadcast':
                    self.energy -= self.find_distance(
                        [position for neighbor_id, position in self.neighbors if neighbor_id == link[1]][0])*1.2
                    logging.info('data from %s to %s, energy:%s' % (self.node_id, link[1], self.energy))
                self.send_neighbor(message_id, message, link[1])
        if self.energy < self.minimum_budget:
            self.alive = False

    def receive_cheapest_link(self, level):
        """
        Node waits for the incoming neighbor message from the leader asking to find the cheapest link (if not leader),
        floods it to other connected neighbors and then waits for the answers with the cheapest links from every
        node that does not have a path to the leader through this node. After all expected messages have been
        received - send a cheapest link to the node that asked to find it.
        :param level: The current level of MST algorithm
        :return: The cheapest currently known link (if leader - that's indeed the cheapest link within the component)
        """
        # Wait for expected number of messages
        # Every neighbor in MST will eventually need to send exactly one message (1 asks to find the cheapest link,
        # others sends the cheapest link)
        expected_messages = self.get_links_in_mst_from_me()
        # Find the cheapest link within this node and neighbors that are not in this connected component
        cheapest_link = self.find_cheapest_link()
        node_to_leader = None
        while True:
            if expected_messages == 0:
                break
            if self.message_queue[self.node_id].empty():
                continue
            communication_type, message_id, message, sender_id = self.message_queue[self.node_id].get()
            # Make sure that base station does not send termination message if message queue is empty, but
            # node is still performing some actions. This will be only crucial in huge networks.
            if communication_type == 'care':
                continue
            self.message_queue[self.node_id].put(('care', None, None, None))
            if message['type'] == 'find_cheapest_link':
                self.flood_tree(message_id, message=message, except_nodes=[sender_id])
                node_to_leader = sender_id
                expected_messages -= 1
            if message['type'] == 'my_cheapest_link':
                cheapest_link = self.compare_two_links(cheapest_link, message['data'])
                expected_messages -= 1
            # If some connected component decides on new link to be added faster than this connected component
            # and sends link decision to this node - put this message back to the end of the queue, so that link
            # decision could be made first in this component
            if message['type'] == 'link_decision' or message['type'] == 'my_current_mst':
                self.message_queue[self.node_id].put(('reordering', message_id, message, sender_id))

        # Send back to leader with the cheapest link if this node is not a leader
        if not self.leader:
            self.send_neighbor(level, {'type': 'my_cheapest_link', 'data': cheapest_link}, node_to_leader)
        return cheapest_link

    def receive_neighbor(self, level=None):
        """
        Receives all neighbor messages that are not related to cheapest link findings. It waits for a new
        message until it gets message from the base station meaning that no one will send anything new in this round
        and the node can terminate.
        If received link decision message - see if the received link can be added into current MST and add it if
            possible and then flood the remaining tree with the decision.
        If received my current mst message - for each received link, see if link can be added into MST and if
            it was added - flood the remaining tree with the decision.
        If ID proposal was received (means we are already in the merge stage) - check if proposed ID is bigger
            than this node's ID (this node is no longer a leader and will not be elected as a new leader if that's true,
            otherwise the node will be elected if it is a leader and will never receive a bigger ID proposal). It can
            then flood the ID proposal to the remaining tree.
        If large volume of data was received (indicated by data broadcast message type) - flood it to the
            remaining tree.
        :param level: The current level of the MST algorithm
        """
        while True:
            if self.message_queue[self.node_id].empty():
                continue
            communication_type, message_id, message, sender_id = self.message_queue[self.node_id].get()
            if communication_type == 'care':
                continue
            self.message_queue[self.node_id].put(('care', None, None, None))
            if communication_type == 'beacon':
                break
            if message['type'] == 'link_decision':
                self.add_link_to_mst(message['data'], level=level, sender_id=sender_id)
                self.flood_tree(level, message={'type': 'link_decision', 'data': message['data']},
                                except_nodes=[sender_id])
            if message['type'] == 'my_current_mst':
                for link in message['data']:
                    added = self.add_link_to_mst(link, level=level, sender_id=sender_id)
                    if added:
                        self.flood_tree(level, message={'type': 'link_decision', 'data': link}, except_nodes=[sender_id])
            if message['type'] == 'id_proposal':
                if message['data'] > self.node_id:
                    self.leader = False
                    self.elected = False
                else:
                    if self.leader:
                        self.elected = True
                # Flood proposal to others in the tree (except the sender)
                self.flood_tree(message_id, message=message, except_nodes=[sender_id])
            if message['type'] == 'data_broadcast':
                self.flood_tree(message=message, except_nodes=[sender_id])

    def compare_two_links(self, link_one, link_two):
        """
        Find the link with the minimum distance from the connected component by comparing two links.
        If one of them is None, receive another one.
        :param link_one: First link to be compared in the form - (minimum distance, link)
        :param link_two: Second link to be compared
        :return: Link with the smaller distance
        """
        if not link_one:
            return link_two
        if not link_two:
            return link_one
        return min(link_one, link_two)

    def add_link_to_mst(self, cheapest_link, level=None, sender_id=None):
        """
        See if a new received link can be added into this node's MST.
        If the link is already in MST - we are done.
        If link includes two of this node's neighbors but not himself - include the link into MST.
        If link includes this node - add the link into MST and inform the neighbor that sent this link with the
            my current mst message just to make sure sender knows about this node's current MST that he might be
            missing.
        :param cheapest_link: The link to be considered for addition into MST
        :param level: The current level of MST algorithm
        :param sender_id: The ID of the sender who sent this link.
        :return:
        """
        if cheapest_link in self.mst or (cheapest_link[1], cheapest_link[0]) in self.mst:
            return False

        if self.is_neighbor(cheapest_link[0]) and self.is_neighbor(cheapest_link[1]):
            self.mst.append(cheapest_link)
            return True

        new_link = None
        if self.node_id == cheapest_link[0]:
            new_link = cheapest_link
        if self.node_id == cheapest_link[1]:
            new_link = (self.node_id, cheapest_link[0])
        if new_link:
            if sender_id:
                self.send_neighbor(level, {'type': 'my_current_mst', 'data': self.mst}, sender_id)
            self.mst.append(new_link)

        return True if new_link else False

    def find_distance(self, position):
        """
        Find distance between two nodes.
        :param position: Position of the other node
        :return: The distance between this and given node
        """
        return math.sqrt((position[0] - self.position[0])**2 + (position[1] - self.position[1])**2)

    def start_bcst(self, sender):
        """
        Start broadcasting large volume data if the node is the one that initiates the broadcast.
        Otherwise just wait for neighbor messages.
        :param sender: The ID of the node that initiates the broadcast.
        """
        if self.node_id == sender:
            self.flood_tree(message={'type': 'data_broadcast'})
        self.receive_neighbor()