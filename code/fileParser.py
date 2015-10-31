from Node import Node


def parse_file(file_to_parse):
    """
    Parses the file
    :param file_to_parse: File name to be parsed
    :return: Array of Node objects and list of bcsts to be performed
    """

    f = open(file_to_parse, 'r')

    # Extract minimum budget
    mb = f.readline()
    Node.minimum_budget = float(mb)

    # Extract nodes and bcsts
    nodes = []
    bcsts = []
    for line in f:
        data = line.split()
        if data[0] == 'node':
            # Create a new Node object
            nodes.append(Node(data[1][:-1], (data[2][:-1], data[3][:-1]), data[4]))
        if data[0] == 'bcst':
            bcsts.append(int(data[2]))

    f.close()
    return nodes, bcsts
