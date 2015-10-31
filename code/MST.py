from logProducer import alert_leaders_to_start_level, new_leaders_elected, new_links_added, nodes_dead
import threading
import Queue
import math

R = 10
events_queue = Queue.Queue()


def find_MST(nodes, need_logging=False):
    """
    Performs SynchGHS algorithm to find MST
    :param nodes: List of all known nodes
    :param need_logging: Flag specifying if logging is required
    :return:
    """

    # Alert all nodes to start constructing the MST by asking them to discover their neighbors
    alert_all(nodes, action='discover', args=[events_queue])

    # Every node should have broadcast a discover message at this point.
    # Route their message to all nodes that are present in a radius R meters around their locations.
    while not events_queue.empty():
        event = events_queue.get()
        if event[0] == 'discover':
            reach_neighbors(nodes, event[1], event[2])

    # Alert all nodes to start responding to discover messages
    alert_all(nodes, action='discover_response', handle=True, handle_message=('beacon', None, None))

    # Start an actual MST algorithm
    # It works in levels starting from level 0 and terminates then no more new links have been added into MST.
    # At each level base station alerts nodes to choose the best link within connected component to be added and
    # then alerts nodes to merge - elect a new leader within every merged connected component.
    level = 0
    while True:
        alert_leaders_to_start_level(nodes, need_logging)
        alert_all(nodes, 'choose_best_link', args=[level, events_queue], handle=True)
        # If no more new links added - terminate, MST is found.
        if events_queue.qsize() == 0:
            break
        new_links_added(events_queue, need_logging)
        alert_all(nodes, 'merge', args=[level], handle=True)
        new_leaders_elected(nodes, need_logging)
        level += 1


def alert_all(nodes, action, args=(), handle=False, handle_message=('beacon', None, None, None), check=10):
    """
    Creates a thread for each of the nodes and triggers given action. It then waits for each of the nodes to finish
     executing. Optionally it can also handle termination then nodes are waiting for a new message, but no one
     is sending any.
    :param nodes: The list of nodes that needs to be alerted
    :param action: The action to be triggered
    :param args: Arguments to be passed into the action function
    :param handle: Boolean flag specifying if termination handling needs to be done
    :param handle_message: Message to be send to all nodes to terminate. Required only id handle=True
    :param check: Number of consecutive times all nodes are sitting idle before sending a termination message.
                Only required if handle=True
    """
    threads = []
    for node in nodes:
        action_options = {'discover': node.discover,
                          'discover_response': node.discover_response,
                          'choose_best_link': node.choose_best_link,
                          'merge': node.merge,
                          'start_bcst': node.start_bcst}
        t = threading.Thread(target=action_options[action], args=args)
        threads.append(t)
        t.start()

    if handle:
        handle_termination(nodes, handle_message, check)

    # Wait for all nodes to finish
    for t in threads:
        t.join()


def handle_termination(nodes, message, check):
    """
    Handle termination then nodes are waiting for a new message, but no one is sending any new.
    :param nodes: List of nodes
    :param message: Message to sent to terminate
    :param check: Number of consecutive times all nodes are sitting idle before sending a termination message
    """
    init = check
    while check > 0:
        state = any([not node.message_queue[node.node_id].empty() for node in nodes])
        check = init if state else check - 1
        continue
    for node in nodes:
        node.message_queue[node.node_id].put(message)


def reach_neighbors(nodes, node_id, node_position):
    """
    Function used only for routing initial discover messages from one node to another within the distance R.
    :param nodes: The list of all known nodes
    :param node_id: The ID of the node that sends discover message
    :param node_position: The location of the node that send discover message
    """

    for node in nodes:
        if node.node_id == node_id:
            continue
        distance = find_distance(node_position, node.position)
        if distance <= R:
            # If node is present in a radius R around the node that is searching
            # ask this node to send discover response message back to the searching node
            node.message_queue[node.node_id].put(('discover', node_id, node_position))


def find_distance(position_a, position_b):
    """
    Find distance between two nodes
    :param position_a: The location of first node in the form (x1, y1)
    :param position_b: The location of the second node in the form (x2, y2)
    :return: Euclidean distance between two nodes
    """
    return math.sqrt((position_a[0] - position_b[0])**2 + (position_a[1] - position_b[1])**2)


def clean(nodes):
    """
    Clean nodes. Done only before the new MST is needed to be found.
    :param nodes: The list of existing alive nodes
    """
    for node in nodes:
        node.leader = True
        node.elected = False
        node.neighbors = []
        node.mst = []
        node.message_queue[node.node_id] = Queue.Queue()


def handle_dead_nodes(given_nodes):
    """
    Check if any of the given nodes is dead and if yes then log them, remove from the nodes list, clean
    all the nodes that are still alive and recompute the MST.
    :param given_nodes: List of nodes
    :return: List of nodes with calculated new MST excluding dead nodes
    """
    dead_nodes = [node for node in given_nodes if not node.alive]
    if dead_nodes:
        nodes_dead(dead_nodes)
        given_nodes = [node for node in given_nodes if node.alive]
        clean(given_nodes)
        find_MST(given_nodes)

    return given_nodes