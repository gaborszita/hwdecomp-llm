import json
import ollama
import re

with open("generate_blif_output.json", "r") as file:
  data = json.load(file)

prompt = """Convert the following BLIF code to Verilog (not SystemVerilog).
Always generate the Verilog code—do not provide only a description.
Use only standard Verilog-2001 syntax, and keep the code as simple and minimal as possible.
Wrap the output in a code block using triple backticks, and begin the block with verilog for proper syntax highlighting.

When implementing logic (e.g., multiplexers or case statements), try to reduce redundancy.
Use concise constructs such as assign y = d[sel]; instead of large case blocks when functionally equivalent.
Prefer using generate loops, assign, or for loops where allowed by Verilog-2001 and appropriate for clarity and brevity."""

num_matches = 0

for idx, circuit in enumerate(data):
  blif_content = circuit["blif"]
  response: ollama.ChatResponse = ollama.chat(model='codellama:7b', messages=[
    {
      'role': 'user',
      'content': prompt + '\n```blif\n' + blif_content + '\n```'
    }
  ])

  pattern = r"```verilog\s+(.*?)```"
  match = re.search(pattern, response.message.content, re.DOTALL)
  if match:
    verilog_code_recovered = match.group(1).strip()
    circuit["verilog_recovered"] = verilog_code_recovered
    num_matches += 1
    #print("Recovered code: ")
    #print(verilog_code_recovered)
  else:
    circuit["verilog_recovered"] = None
    #print("No matches for module " + circuit["moduleName"])
    #print(response.message.content)

  print(f"Progress: {idx + 1}/{len(data)}")

with open("recovered_verilog.json", "w") as file:
  json.dump(data, file, indent=2)

print(f"Total matches found: {num_matches}/{len(data)}")