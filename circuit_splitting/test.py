from jinja2 import Template

with open("templates/partitioned_circuit_coa_question_asker.j2", "r") as f:
  question_asker_template_str = f.read()

question_asker_template = Template(question_asker_template_str)
question_asker_input = question_asker_template.render({
  "last_agent_response": "hi"
})

print(question_asker_input)