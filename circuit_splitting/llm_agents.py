from typing import List, Optional
from openai import OpenAI
from jinja2 import Template
import os

class Agent:
  def __init__(self, data_chunk):
    self.data_chunk = data_chunk

class PartitionedCircuitChainOfAgents:
  def __init__(self, top_module_code: str, submodules: List[str], client: OpenAI, model: str):
    self.top_module_code = top_module_code
    self.submodules = submodules
    self.client = client
    self.model = model
  
  def ask_question(self, question: str, log_dir: Optional[str] = None) -> str:
    with open("templates/partitioned_circuit_chain_of_agents_worker_prompt.j2", "r") as f:
      worker_prompt_template_str = f.read()
    worker_prompt_template = Template(worker_prompt_template_str)
    if log_dir is not None:
      with open("templates/prompt_response_log.j2", "r") as f:
        log_template_str = f.read()
      log_template = Template(log_template_str)
    with open("templates/partitioned_circuit_chain_of_agents_manager_prompt.j2", "r") as f:
      manager_prompt_template_str = f.read()
    manager_prompt_template = Template(manager_prompt_template_str)
    previous_response = None
    # worker agents process submodules
    for idx, submodule in enumerate(self.submodules):
      data = {
        "top_module_code": self.top_module_code,
        "current_submodule_code": submodule,
        "question": question,
        "previous_agent_response": previous_response
      }
      prompt = worker_prompt_template.render(data)
      messages = [{
        "role": "user",
        "content": prompt
      }]
      response = self.client.chat.completions.create(model=self.model, messages=messages, stream=False)
      response = response.choices[0].message.content
      if log_dir is not None:
        log_str = log_template.render({
          "prompt": prompt,
          "response": response
        })
        with open(os.path.join(log_dir, f"submodule_{idx}_agent_response.txt"), "w") as f:
          f.write(log_str)
      previous_response = response

    # manger agent generates final summary
    prompt = manager_prompt_template.render({
      "last_agent_response": response,
      "question": question
    })
    messages = [{
      "role": "user",
      "content": prompt
    }]
    response = self.client.chat.completions.create(model=self.model, messages=messages, stream=False)
    response = response.choices[0].message.content
    if log_dir is not None:
      log_str = log_template.render({
        "prompt": prompt,
        "response": response
      })
      with open(os.path.join(log_dir, "manager_agent_response.txt"), "w") as f:
        f.write(log_str)
    return response

class Chat:
  def __init__(self, client: OpenAI, model: str, log_dir: Optional[str]):
    self.client = client
    self.model = model
    self.log_dir = log_dir
    if log_dir is not None:
      with open("templates/CHAT_response_log.j2", "r") as f:
        log_template_str = f.read()
      self.log_template = Template(log_template_str)
      self.log_idx = 0
    self.chat_history = []

  def send(self, user_message, role="user"):
    self.chat_history.append({"role": role, "content": user_message})
    response = self.client.chat.completions.create(model=self.model, messages=self.chat_history, stream=False)
    self.chat_history.append({"role": "assistant", "content": response.choices[0].message.content})
    if self.log_dir is not None:
      log_str = self.log_template.render({
          "messages": self.chat_history
        })
      with open(os.path.join(self.log_dir, f"submodule_{self.log_idx}_agent_response.txt"), "w") as f:
        f.write(log_str)
      self.log_idx += 1
    return response.choices[0].message.content

  def reset(self):
    self.chat_history = []