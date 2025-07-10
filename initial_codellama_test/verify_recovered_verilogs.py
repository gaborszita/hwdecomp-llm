import json
import os
import shutil
import subprocess

EQY_PATH = '/Users/gabi/oss-cad-suite/bin/eqy'

with open("recovered_verilog.json", "r") as file:
  data = json.load(file)

correct_count = 0
recovered_verilog_code_count = 0

for circuit in data:
  verilog_code_recovered = circuit["verilog_recovered"]
  if verilog_code_recovered is not None:
    recovered_verilog_code_count += 1
    recovered_verilog_code_path = os.path.join(os.getcwd(), "v_recovered.v")
    with open(recovered_verilog_code_path, "w") as f:
      f.write(verilog_code_recovered)
    correct_verilog_code_path = os.path.join(os.getcwd(), "v_correct.v")
    with open(correct_verilog_code_path, "w") as f:
      f.write(circuit["verilog"])
    module_name = circuit["moduleName"]
    eqy_content = f"""
    [gold]
    read_verilog {correct_verilog_code_path}
    prep -top {module_name}

    [gate]
    read_verilog {recovered_verilog_code_path}
    prep -top {module_name}

    [strategy simple]
    use sby
    """;

    eqy_config_path = os.path.join(os.getcwd(), "eqy_config.eqy")
    with open(eqy_config_path, "w") as f:
      f.write(eqy_content)
    
    eqy_working_dir = os.path.join(os.getcwd(), "eqy_working_dir")
    if os.path.exists(eqy_working_dir):
      shutil.rmtree(eqy_working_dir)
    
    result_recovered = subprocess.run([EQY_PATH, eqy_config_path, '-d', eqy_working_dir], capture_output=True, text=True)

    if result_recovered.returncode == 0:
      correct_count += 1
      print(f"Verification passed for module {module_name}.")
    else:
      print(f"Verification failed for module {module_name}.")
      print(result_recovered.stdout)
      print(result_recovered.stderr)
    
    os.remove(recovered_verilog_code_path)
    os.remove(correct_verilog_code_path)
    os.remove(eqy_config_path)
    if os.path.exists(eqy_working_dir):
      shutil.rmtree(eqy_working_dir)

  else:
    print(f"No recovered Verilog code for module {circuit['moduleName']}.")

print(f"Overall Verilog recovery rate: {correct_count}/{len(data)} = {correct_count / len(data):.2%}")
print(f"Correct Verilog recovery rate among circuits that have a recovered "
      f"Verilog code: {correct_count}/{recovered_verilog_code_count} = {correct_count / recovered_verilog_code_count:.2%}")