import kagglehub
from datasets import load_dataset
import pandas as pd
import os
import re
from pyosys import libyosys as ys
import json
import subprocess

path = kagglehub.dataset_download("sohamndeshmukh/verilog-code-dataset")
df = pd.read_csv(os.path.join(path, "formatted_small_df.csv"))
verilog_codes = df["Correct"]

#ds = load_dataset("shailja/Verilog_GitHub", streaming=True, split="train")

blif_files_dir = os.path.join(os.getcwd(), "blif_files")

out = []

for idx, verilog_code in enumerate(verilog_codes[:100]):
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
  except subprocess.CalledProcessError as e:
    print("Caught error while running yosys:")
    print(e.stderr)
    success = False

  if success:
    with open(blif_out_file, "r") as file:
      blif_content = file.read()

    os.remove(blif_out_file)
    os.remove(verilog_code_path)

    out.append({
      "moduleName": module_name,
      "verilog": verilog_code,
      "blif": blif_content
    })

  print(f"Progress: {idx}/{len(verilog_codes)}")

with open("generate_blif_output.json", "w") as file:
  json.dump(out, file, indent=2)