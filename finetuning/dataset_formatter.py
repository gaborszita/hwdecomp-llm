import json
import pandas as pd
from datasets import Dataset
from unsloth import to_sharegpt, standardize_sharegpt, apply_chat_template, FastLanguageModel

CHAT_TEMPLATE = """Below are some instructions that describe some tasks. Write responses that appropriately complete each request.

### Instruction:
{INPUT}

### Response:
{OUTPUT}"""

def format_dataset(dataset, tokenizer):
  pandas_ds = pd.DataFrame(dataset)
  #pandas_ds['empty'] = '' # little trick to prevent unsloth from making instruction part of a tuple
  huggingface_ds = Dataset.from_pandas(pandas_ds)
  #print(huggingface_ds[0])
  huggingface_ds_sharegpt = to_sharegpt(
    huggingface_ds,
    #merged_prompt="{instruction}[[{empty}]]",
    merged_prompt="{instruction}",
    output_column_name="output",
    conversation_extension=1,
  )
  #print(huggingface_ds_sharegpt[0])
  huggingface_ds_sharegpt_standardized = standardize_sharegpt(huggingface_ds_sharegpt)
  #print(huggingface_ds_sharegpt_standardized[0])
  dataset_templated = apply_chat_template(
    huggingface_ds_sharegpt_standardized,
    tokenizer=tokenizer,
    chat_template=CHAT_TEMPLATE,
  )
  return dataset_templated

if __name__ == "__main__":
  with open("train_data.json", "r") as f:
    dataset = json.load(f)

  max_seq_length = 2048 # Choose any! We auto support RoPE Scaling internally!
  dtype = None # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
  load_in_4bit = True # Use 4bit quantization to reduce memory usage. Can be False.
  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/codellama-7b-bnb-4bit",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
    # token = "hf_...", # use one if using gated models like meta-llama/Llama-2-7b-hf
  )
  ds_formatted = format_dataset(dataset, tokenizer)
  print(ds_formatted[0])