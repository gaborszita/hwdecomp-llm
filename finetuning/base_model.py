from unsloth import FastLanguageModel, to_sharegpt, apply_chat_template, standardize_sharegpt
from datasets import Dataset
from dataset_formatter import CHAT_TEMPLATE
import pandas as pd
from model_output_generator import generate_model_outputs
from dataset_formatter import format_dataset

def generate_base_model_outputs(dataset):
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

  format_dataset(dataset, tokenizer)

  return generate_model_outputs(dataset, model, tokenizer)