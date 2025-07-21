import pyrtl
from pyrtl import *
import collections
import igraph as ig
import leidenalg as la
import os
import shutil

def partition_circuit(out_dir):
  svg_dir = os.path.join(out_dir, "svg_out")
  verilog_dir = os.path.join(out_dir, "verilog_out")
  os.mkdir(svg_dir)
  os.mkdir(verilog_dir)

  def block_to_graphviz_string(
      block: Block = None, namer=pyrtl.visualization._graphviz_default_namer,
      split_state: bool = True, maintain_arg_order: bool = False, node_colors: dict = None,
      node_color_all: str = None):
    graph = net_graph(block, split_state)
    node_index_map = {}  # map node -> index

    rstring = """\
digraph g {
  graph [splines="spline", outputorder="edgesfirst"];
  node [shape=circle, style=filled, fillcolor=lightblue1,
      fontcolor=black, fontname=helvetica, penwidth=0,
      fixedsize=shape];
  edge [labelfloat=false, penwidth=2, color=deepskyblue, arrowsize=.5];
"""
    from pyrtl.importexport import _natural_sort_key

    def _node_sort_key(node):
      # If a LogicNet and a wire share the same name, we want the LogicNet
      # to sort first, so we arbitrarily 'A' and 'B' suffixes to break ties.
      if isinstance(node, LogicNet):
        if node.op == '@':
          key = str(node.args[2]) + 'A'
        else:
          key = node.dests[0].name + 'A'
      else:
        key = node.name + 'B'
      return _natural_sort_key(key)

    # print the list of nodes
    for index, node in enumerate(sorted(graph.keys(), key=_node_sort_key)):
      label = namer(node, False, False, split_state)
      color = None
      if node_colors and node in node_colors:
        color = node_colors[node]
      elif node_color_all:
        color = node_color_all
      if color is not None:
        if label:
          label = label[:-1] + ', fillcolor="%s"]' % color
        else:
          label = '[fillcolor="%s"]' % color
      rstring += '  n%s %s;\n' % (index, label)
      node_index_map[node] = index

    # print the list of edges
    srcs = collections.defaultdict(list)
    for _from in sorted(graph.keys(), key=_node_sort_key):
      for _to in sorted(graph[_from].keys(), key=_node_sort_key):
        from_index = node_index_map[_from]
        to_index = node_index_map[_to]
        for edge in graph[_from][_to]:
          is_to_splitmerge = True if hasattr(_to, 'op') and _to.op in 'cs' else False
          label = namer(edge, True, is_to_splitmerge, False)
          rstring += '  n%d -> n%d %s;\n' % (from_index, to_index, label)
          srcs[_to].append((_from, edge))

    # Maintain left-to-right order of incoming wires for nets where order matters.
    # This won't be visually perfect sometimes (especially for a wire used twice
    # in a net's argument list), but for the majority of cases this will improve
    # the visualization.
    def index_of(w, args):
      # Special helper so we compare id rather than using builtin operators
      ix = 0
      for arg in args:
        if w is arg:
          return ix
        ix += 1
      raise PyrtlInternalError('Expected to find wire in set of args')

    if maintain_arg_order:
      block = working_block(block)
      for net in sorted(block.logic_subset(op='c-<>x@'), key=_node_sort_key):
        args = [(node_index_map[n], wire) for (n, wire) in srcs[net]]
        args.sort(key=lambda t: index_of(t[1], net.args))
        s = ' -> '.join(['n%d' % n for n, _ in args])
        rstring += '  {\n'
        rstring += '    rank=same;\n'
        rstring += '    edge[style=invis];\n'
        rstring += '    ' + s + ';\n'
        rstring += '    rankdir=LR;\n'
        rstring += '  }\n'

    rstring += '}\n'
    return rstring

  def block_to_svg(block: Block = None, split_state: bool = True, maintain_arg_order: bool = False,
                  node_colors: dict = None, node_color_all: str = None):
    from graphviz import Source
    src = Source(block_to_graphviz_string(block, split_state=split_state,
                                          maintain_arg_order=maintain_arg_order,
                                          node_colors=node_colors,
                                          node_color_all=node_color_all))
    return src._repr_image_svg_xml()

  node_colors = dict()
  block = pyrtl.working_block()
  pyrtl_graph = pyrtl.net_graph()
  g = ig.Graph()

  str_to_node_map = dict()

  for node in pyrtl_graph.keys():
    g.add_vertex(str(node))
    str_to_node_map[str(node)] = node

  for node, edges in pyrtl_graph.items():
    for adjacent_node, edge in edges.items():
      g.add_edge(str(node), str(adjacent_node))

  #partition = la.find_partition(g, la.ModularityVertexPartition)

  partition = la.find_partition(g, la.CPMVertexPartition,
                                  resolution_parameter = 0.005)

  svg_distinct_colors = [
    "red", "blue", "green", "orange", "purple",
    "cyan", "magenta", "yellow", "lime", "pink",
    "brown", "teal", "gold", "indigo", "orchid",
    "crimson", "navy", "salmon", "turquoise", "violet",
    "olive", "coral", "skyblue", "forestgreen", "maroon",
    "deeppink", "chocolate", "darkslateblue", "chartreuse", "mediumseagreen"
  ]

  print(f"Number of partitions: {len(partition)}")

  for i, community in enumerate(partition):
    for node in community:
      nodeMap = str_to_node_map[g.vs[node]['name']]
      node_colors[nodeMap] = svg_distinct_colors[i]
      #print(g.vs[node]['name'] in str_to_node_map)
    #print(f"Community {i+1}: {[g.vs[node]['name'] for node in community]}")

  block = pyrtl.working_block()
  with open(os.path.join(svg_dir, "circuit_out.svg"), "w") as file:
    print(block_to_svg(block, True, node_colors=node_colors), file=file)

  wirevector_driver = dict()
  wirevector_users = dict()

  for i, community in enumerate(partition):
    for node in community:
      node_map = str_to_node_map[g.vs[node]['name']]
      if isinstance(node_map, LogicNet):
        for dest in node_map.dests:
          if dest not in wirevector_driver:
            wirevector_driver[dest] = i
          else:
            raise Exception("WireVector has multiple drivers!")
        for arg in node_map.args:
          if arg not in wirevector_users:
            wirevector_users[arg] = set()
          wirevector_users[arg].add(i)

  convert_to_input_wirevector_set = set()

  add_output_wirevector_set = set()
  convert_to_output_wirevector_set = set()

  for wv in block.wirevector_set:
    driver_partition = wirevector_driver.get(wv, None)
    user_partitions = wirevector_users.get(wv, set())

    if driver_partition is not None:
      if len(user_partitions) > 1 or (len(user_partitions) == 1 and driver_partition not in user_partitions):
        add_output_wirevector_set.add((wv, driver_partition))
        for user_partition in user_partitions:
          if user_partition != driver_partition:
            convert_to_input_wirevector_set.add((wv, user_partition))
      elif len(user_partitions) == 1 and driver_partition not in user_partitions:
        convert_to_output_wirevector_set.add((wv, driver_partition))
        for user_partition in user_partitions:
          convert_to_input_wirevector_set.add((wv, user_partition))

  internal_wire_idx = 0
  internal_wire_mappings = {}
  def internal_wire_mapping(name):
    nonlocal internal_wire_idx
    nonlocal internal_wire_mappings
    if name not in internal_wire_mappings:
      internal_wire_mappings[name] = "internal_" + str(internal_wire_idx)
      internal_wire_idx += 1
    return internal_wire_mappings[name]

  io_wire_idx = 0
  io_wire_mappings = {}
  def io_wire_mapping(name):
    nonlocal io_wire_idx
    nonlocal io_wire_mappings
    if name not in io_wire_mappings:
      io_wire_mappings[name] = "io_" + str(io_wire_idx)
      io_wire_idx += 1
    return io_wire_mappings[name]

  intermediate_io_wire_idx = 0
  intermediate_io_wire_mappings = {}
  def intermediate_io_wire_mapping(name):
    nonlocal intermediate_io_wire_idx
    nonlocal intermediate_io_wire_mappings
    if name not in intermediate_io_wire_mappings:
      intermediate_io_wire_mappings[name] = "intermediate_io_" + str(intermediate_io_wire_idx)
      intermediate_io_wire_idx += 1
    return intermediate_io_wire_mappings[name]

  for i, community in enumerate(partition):
    new_block = pyrtl.Block()
    wirevector_mappings = dict()
    for node in community:
      node_map = str_to_node_map[g.vs[node]['name']]
      if isinstance(node_map, LogicNet):
        def get_mapping(wv):
          if wv not in wirevector_mappings:
            if isinstance(wv, pyrtl.Input):
              wirevector_mappings[wv] = pyrtl.Input(bitwidth=wv.bitwidth, name=io_wire_mapping(wv.name), block=new_block)
            elif (wv, i) in convert_to_input_wirevector_set:
              wirevector_mappings[wv] = pyrtl.Input(bitwidth=wv.bitwidth, name=intermediate_io_wire_mapping(wv.name), block=new_block)
            elif isinstance(wv, pyrtl.Output):
              wirevector_mappings[wv] = pyrtl.Output(bitwidth=wv.bitwidth, name=io_wire_mapping(wv.name), block=new_block)
            elif (wv, i) in convert_to_output_wirevector_set:
              wirevector_mappings[wv] = pyrtl.Output(bitwidth=wv.bitwidth, name=intermediate_io_wire_mapping(wv.name), block=new_block)
            elif isinstance(wv, pyrtl.Const):
              wirevector_mappings[wv] = pyrtl.Const(val=wv.val, bitwidth=wv.bitwidth, name=internal_wire_mapping(wv.name), block=new_block)
            elif isinstance(wv, pyrtl.Register):
              wirevector_mappings[wv] = pyrtl.Register(bitwidth=wv.bitwidth, name=internal_wire_mapping(wv.name), block=new_block)
            elif isinstance(wv, pyrtl.WireVector):
              wirevector_mappings[wv] = pyrtl.WireVector(bitwidth=wv.bitwidth, name=internal_wire_mapping(wv.name), block=new_block)
            
            if (wv, i) in add_output_wirevector_set:
              output = pyrtl.Output(bitwidth=wv.bitwidth, name=intermediate_io_wire_mapping(wv.name), block=new_block)
              new_block.add_net(pyrtl.LogicNet(
                op="w",
                op_param=None,
                args=(wirevector_mappings[wv],),
                dests=(output,)
              )) 
          return wirevector_mappings[wv]

        args = tuple(map(lambda wv: get_mapping(wv), node_map.args))
        dests = tuple(map(lambda wv: get_mapping(wv), node_map.dests))

        new_net = pyrtl.LogicNet(
          op=node_map.op,
          op_param=node_map.op_param,
          args=args,
          dests=dests
        )

        new_block.add_net(new_net)
    new_block.sanity_check()

    with open(os.path.join(svg_dir, "partition_" + str(i) + ".svg"), "w") as file:
      print(block_to_svg(new_block, True, node_color_all=svg_distinct_colors[i]), file=file)
    with open(os.path.join(verilog_dir, "module_" + str(i) + ".v"), "w") as file:
      pyrtl.output_to_verilog(file, block=new_block)
    
    print(f"Processed partition {i}")

  with open(os.path.join(verilog_dir, "original_block.v"), "w") as file:
    pyrtl.output_to_verilog(file)
  print(f"Created original block file")


if __name__ == "__main__":
  circuits_dir = "circuits"
  partitioned_circuits_dir = "circuits_partitioned"
  if os.path.exists(partitioned_circuits_dir):
    shutil.rmtree(partitioned_circuits_dir)
  os.mkdir(partitioned_circuits_dir)
  for filename in os.listdir(circuits_dir):
    print(f"Processing {filename}")
    with open(os.path.join(circuits_dir, filename), "r") as f:
      pyrtl.reset_working_block()
      exec(f.read())
      circuit_name = os.path.splitext(filename)[0]
      os.mkdir(os.path.join(partitioned_circuits_dir, circuit_name))
      partition_circuit(os.path.join(partitioned_circuits_dir, circuit_name))