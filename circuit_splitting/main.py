from llm_agents import PartitionedCircuitChainOfAgents, Chat
from openai import OpenAI
import os
from dotenv import load_dotenv
from jinja2 import Template
import shutil
import re

load_dotenv()

client = OpenAI()
model = "gpt-4.1"

circuit_dir = "circuits_partitioned/fsm_big_1/postprocessed_verilog_out"

with open(os.path.join(circuit_dir, "top_module.v"), "r") as f:
  top_module_code = f.read()

submodules = []
for filename in os.listdir(circuit_dir):
  if filename.endswith(".v") and filename != "top_module.v":
    with open(os.path.join(circuit_dir, filename), "r") as f:
      submodules.append(f.read())

coa = PartitionedCircuitChainOfAgents(top_module_code=top_module_code,
                                      submodules=submodules,
                                      client=client,
                                      model=model)

if os.path.exists("logs"):
  shutil.rmtree("logs")
os.mkdir("logs")
os.mkdir("logs/chain_of_agents")
os.mkdir("logs/question_asker")

#coa.ask_question("What are the registers in this circuit?", log_dir="logs")

with open("templates/partitioned_circuit_coa_question_asker.j2", "r") as f:
  question_asker_template_str = f.read()

question_asker_template = Template(question_asker_template_str)
question_asker_input = question_asker_template.render({
  "last_agent_response": None
})
question_asker_chat = Chat(client, model, "logs/question_asker")

question_asker_response = question_asker_chat.send(question_asker_template.render({"last_agent_response": None}))

log_idx = 0
while len(re.findall(r'\[QUESTION\](.*?)\[/QUESTION\]', question_asker_response, re.DOTALL)) != 0:
  question = re.findall(r'\[QUESTION\](.*?)\[/QUESTION\]', question_asker_response, re.DOTALL)[0]
  coa_log_dir = f"logs/chain_of_agents/question_{log_idx}"
  os.mkdir(coa_log_dir)
  coa_response = coa.ask_question(question, coa_log_dir)
  log_idx += 1

  question_asker_response = question_asker_chat.send(question_asker_template.render({
    "last_agent_response": coa_response
  }))

print("No question found, final answer:")
print(question_asker_response)