import re
import os
import shutil
import glob
from pyverilog.vparser.parser import parse
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
import pyverilog.vparser.ast as vast

def postprocess_partitions(in_dir, out_dir):
  pattern = re.compile(r'(module_\d+)\.v')
  matching_files = [f for f in os.listdir(in_dir) if pattern.fullmatch(f)]

  print("Matching files:", matching_files)

  io_list = {}
  io_list_objects = set()

  for filename in matching_files:
    base_name = pattern.fullmatch(filename).group(1)
    new_module_name = base_name

    ast, directives = parse([os.path.join(in_dir, filename)], debug=False)

    inputs = []
    outputs = []
    inouts = []

    for desc in ast.description.definitions:
      if desc.name == "toplevel":
        desc.name = new_module_name
        for port in desc.portlist.ports:
          portname = port.name
          found = False
          for item in desc.items:
            if isinstance(item, vast.Decl):
              for elem in item.list:
                if elem.name == portname:
                  io_list_objects.add(elem)
                  if isinstance(elem, vast.Input):
                    inputs.append(portname)
                  elif isinstance(elem, vast.Output):
                    outputs.append(portname)
                  elif isinstance(elem, vast.Inout):
                    inouts.append(portname)
                  else:
                    raise Exception("Invalid port type!")
                  found = True
          if not found:
            raise Exception("Unable to find port type!")
      module = desc

    codegen = ASTCodeGenerator()
    rslt = codegen.visit(ast)

    # Save to new file
    new_filename = f"{base_name}_postprocessed.v"
    with open(os.path.join(out_dir, new_filename), "w") as f:
      f.write(rslt)
    
    io_list[new_module_name] = {
      "inputs": inputs,
      "outputs": outputs,
      "inouts": inouts
    }

    print(f"Processed {filename} → {new_filename}")

  params = vast.Paramlist( [] )

  ports = []
  items = []

  for io_obj in io_list_objects:
    if io_obj.name.startswith("intermediate_io_"):
      wire = vast.Wire(io_obj.name, io_obj.width, io_obj.signed, io_obj.dimensions, io_obj.value)
      items.append(wire)
    else:
      ports.append(vast.Ioport(io_obj))

  ports = vast.Portlist(ports)

  for module_name, io in io_list.items():
    portlist = []
    for port in io["inputs"] + io["outputs"] + io["inouts"]:
      portlist.append(vast.PortArg(port, vast.Identifier(port)))
    instance = vast.Instance(
      module=module_name,
      name=module_name + "_instance",
      portlist=portlist,
      parameterlist=[]
    )
    inst_list = vast.InstanceList(module_name, [], [instance])
    items.append(inst_list)

  ast = vast.ModuleDef("top", params, ports, items)
      
  codegen = ASTCodeGenerator()
  rslt = codegen.visit(ast)

  top_module_filename = "top_module.v"

  with open(os.path.join(out_dir, top_module_filename), "w") as f:
    print(rslt, file=f)

  print("Processed " + top_module_filename)

if __name__ == "__main__":
  verilog_out_directories = glob.glob('circuits_partitioned/*/verilog_out')
  for dir in verilog_out_directories:
    print(f"Processing directory {dir}")
    out_dir = os.path.join(os.path.dirname(dir), "postprocessed_verilog_out")
    if os.path.exists(out_dir):
      shutil.rmtree(out_dir)
    os.mkdir(out_dir)
    postprocess_partitions(dir, out_dir)