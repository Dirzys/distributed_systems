
def get_file_name():
    return 'log.txt'


def get_file_mode():
    return 'a'


def open_file():
    return open(get_file_name(), get_file_mode())


def alert_leaders_to_start_level(nodes, need_logging):
    """
    Logs the ids of the alerted nodes
    :param nodes: List of all nodes in the network
    :param need_logging: Flag specifying if logging is necessary
    """
    if not need_logging:
        return
    f = open_file()
    # Log only the nodes that are leaders at this stage
    leaders = [str(node.node_id) for node in nodes if node.leader]
    leader_string = ','.join(leaders)
    f.write('bs %s\n' % leader_string)
    f.close()


def new_links_added(links_queue, need_logging):
    """
    Logs the links that have been recently added by the MST
    :param links_queue: Queue of links to be logged
    :param need_logging: Flag specifying if logging is required
    """
    f = open_file()
    previous_links = []
    while True:
        if links_queue.empty():
            break
        _, link = links_queue.get()
        # Make sure we do not log same link but in reversed order
        if (not link in previous_links) and (not (link[1], link[0]) in previous_links) and need_logging:
            link_to_add = (min(link), max(link))
            f.write('added %s-%s\n' % link_to_add)
            previous_links.append(link_to_add)

    f.close()


def new_leaders_elected(nodes, need_logging):
    """
    Logs the leaders that have been elected during the previous level
    :param nodes: List of all nodes in the network
    :param need_logging: Flag specifying if logging is required
    """
    if not need_logging:
        return
    f = open_file()
    for node in nodes:
        # If node was elected in the previous round - log it
        if node.elected:
            f.write('elected %s\n' % node.node_id)

    f.close()


def nodes_dead(nodes):
    """
    Log dead nodes
    :param nodes: List of dead nodes in the network
    """
    f = open_file()
    for node in nodes:
        f.write('node down %s\n' % node.node_id)
    f.close()
