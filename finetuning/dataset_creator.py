import kagglehub
import pandas as pd
import os
import subprocess
import re
import json

prompt = """Convert the following BLIF code to Verilog (not SystemVerilog).
Always generate the Verilog code—do not provide only a description.
Use only standard Verilog-2001 syntax, and keep the code as simple and minimal as possible.
Wrap the output in a code block using triple backticks, and begin the block with verilog for proper syntax highlighting.

When implementing logic (e.g., multiplexers or case statements), try to reduce redundancy.
Use concise constructs such as assign y = d[sel]; instead of large case blocks when functionally equivalent.
Prefer using generate loops, assign, or for loops where allowed by Verilog-2001 and appropriate for clarity and brevity."""

path = kagglehub.dataset_download("sohamndeshmukh/verilog-code-dataset")
df = pd.read_csv(os.path.join(path, "formatted_small_df.csv"))
verilog_codes = df["Correct"]

verilog_codes = verilog_codes.sample(frac=1, random_state=42).reset_index(drop=True)

def create_dataset(limit=None):
  if limit == None:
    limit = len(verilog_codes)

  count = 0
  dataset = []

  for idx, data in enumerate(verilog_codes):
    #verilog_code = data['text']
    verilog_code = data
    match = re.search(r'\bmodule\s+(\w+)', verilog_code)
    if match:
      module_name = match.group(1)
    else:
      #raise Exception("Cannot get module name!")
      print('WARNING: Cannot get module name, skipping!')
      continue

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
      success = False

    if success:
      with open(blif_out_file, "r") as file:
        blif_content = file.read()

      os.remove(blif_out_file)
      os.remove(verilog_code_path)

      instruction = prompt + '\n```blif\n' + blif_content + '\n```'
      output = "```verilog\n" + verilog_code + "\n```"

      if len(instruction) < 20000:
        dataset.append({
          "instruction": instruction,
          "output": output,
          "moduleName": module_name
        })
        count += 1
      else:
        print("Instruction too long, skipping...")
        continue

    #print(f"Progress: {idx+1}/{len(verilog_codes)}")
    print(f"Progress: {count}/{limit}")

    if count >= limit:
      break


  split_idx = int(len(dataset) * 0.8)

  train_data = dataset[:split_idx]
  test_data = dataset[split_idx:]

  train_data_path = os.path.join(os.getcwd(), "train_data.json")
  test_data_path = os.path.join(os.getcwd(), "test_data.json")

  with open(train_data_path, 'w') as f:
    json.dump(train_data, f, indent=2)

  with open(test_data_path, 'w') as f:
    json.dump(test_data, f, indent=2)