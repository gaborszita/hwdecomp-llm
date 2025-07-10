from datasets import load_dataset
import pandas as pd
import re
import os
import subprocess

dataset_verilog_codes = load_dataset("shailja/Verilog_GitHub", split="train")

train_dataset_combined = []

for idx, data in enumerate(dataset_verilog_codes):
  verilog_code = data['text']
  match = re.search(r'\bmodule\s+(\w+)', verilog_code)
  if match:
    module_name = match.group(1)
  else:
    raise Exception("Cannot get module name!")

  verilog_code_path = os.path.join(os.getcwd(), "v_temp.v")
  blif_out_file = os.path.join(os.getcwd(), "out_blif_temp.blif")

  with open(verilog_code_path, "w") as f:
    f.write(verilog_code)
  
  yosys_cmd = [
    "yosys",
    "-p",
    f"read_verilog {verilog_code_path}; tee -q synth -top {module_name}; tee -q write_blif {blif_out_file}"
  ]
  try:
    result = subprocess.run(yosys_cmd, capture_output=True, text=True, check=True)
    success = True
    print("Successfully generated blif!")
  except subprocess.CalledProcessError as e:
    print("Caught error while running yosys:")
    print(e.stderr)
    print(e.stdout)
    print()
    print(yosys_cmd)
    exit()
    success = False

  if success:
    with open(blif_out_file, "r") as file:
      blif_content = file.read()

    os.remove(blif_out_file)
    os.remove(verilog_code_path)

    prompt = """Convert the following BLIF code to Verilog (not SystemVerilog).
Always generate the Verilog code—do not provide only a description.
Use only standard Verilog-2001 syntax, and keep the code as simple and minimal as possible.
Wrap the output in a code block using triple backticks, and begin the block with verilog for proper syntax highlighting.

When implementing logic (e.g., multiplexers or case statements), try to reduce redundancy.
Use concise constructs such as assign y = d[sel]; instead of large case blocks when functionally equivalent.
Prefer using generate loops, assign, or for loops where allowed by Verilog-2001 and appropriate for clarity and brevity."""

    instruction = prompt + '\n```blif\n' + blif_content + '\n```'
    output = "```verilog\n" + verilog_code + "\n```"

    train_dataset_combined.append({
      "instruction": instruction,
      "output": output
    })

  print(f"Progress: {idx}/{len(dataset_verilog_codes)}")