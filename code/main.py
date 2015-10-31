from fileParser import parse_file
from MST import *
from logProducer import get_file_name

# Getting input file name from the user command
if __name__ == "__main__":
    import sys
    file_to_parse = sys.argv[1]

# Parse the file first
nodes, bcsts = parse_file(file_to_parse)

# Find the MST and log the results into the file 'log.txt'
find_MST(nodes, need_logging=True)

# Just in case some nods does not have enough energy at the start of the first bcst
if bcsts:
    nodes = handle_dead_nodes(nodes)

# For each given broadcast perform the broadcast one at the time
for bcst in bcsts:
    if not bcst in [node.node_id for node in nodes]:
        continue
    # Alert all to start sending\receiving a message from sender node
    alert_all(nodes, action='start_bcst', args=[bcst], handle=True)
    # If any of the nodes is dead - clean nodes and recompute MST excluding that node
    nodes = handle_dead_nodes(nodes)
