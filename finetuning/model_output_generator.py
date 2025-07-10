from unsloth import FastLanguageModel, apply_chat_template, standardize_sharegpt, to_sharegpt
from datasets import Dataset
import json
from dataset_formatter import CHAT_TEMPLATE
import pandas as pd

def generate_model_outputs(dataset, model, tokenizer):
  model_outputs = []

  for idx, training_example in enumerate(dataset):
    FastLanguageModel.for_inference(model) # Enable native 2x faster inference
    messages = [                    # Change below!
        {"role": "user", "content": training_example["instruction"]},
    ]
    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt = True,
        return_tensors = "pt",
    ).to("cuda")

    output_ids = model.generate(
      input_ids,
      max_new_tokens=128,
      pad_token_id=tokenizer.eos_token_id,
    )

    generated_ids = output_ids[0][input_ids.shape[-1]:]
    generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)

    model_outputs.append(generated_text)

    print(f"Progress: {idx + 1}/{len(dataset)}")
  
  return model_outputs

if __name__ == "__main__":
  with open("train_data.json", "r") as f:
    dataset = json.load(f)

  max_seq_length = 16384 # Choose any! We auto support RoPE Scaling internally!
  dtype = None # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
  load_in_4bit = True # Use 4bit quantization to reduce memory usage. Can be False.
  model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/codellama-7b-bnb-4bit",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
    # token = "hf_...", # use one if using gated models like meta-llama/Llama-2-7b-hf
  )

  pandas_ds = pd.DataFrame(dataset)
  huggingface_ds = Dataset.from_pandas(pandas_ds)
  huggingface_ds_sharegpt = to_sharegpt(
    huggingface_ds,
    merged_prompt="{instruction}",
    output_column_name="output",
    conversation_extension=1,
  )
  huggingface_ds_sharegpt_standardized = standardize_sharegpt(huggingface_ds_sharegpt)
  dataset_templated = apply_chat_template(
    huggingface_ds_sharegpt_standardized,
    tokenizer=tokenizer,
    chat_template=CHAT_TEMPLATE,
    #chat_template=CHAT_TEMPLATES['llama'][3]
  )

  model_outputs = generate_model_outputs(dataset, model, tokenizer)

  with open("model_outputs.json", "w") as f:
    json.dump(model_outputs, f)