import os
import torch
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

logger = logging.getLogger(__name__)

class RoleplayModel:
    def __init__(self, model_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.load_model()
    
    def load_model(self):
        try:
            logger.info(f"Loading model from: {self.model_path}")
            
            # Verify model directory exists
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model directory not found: {self.model_path}")
            
            # Verify essential files
            required_files = [
                "config.json", 
                "tokenizer.json", 
                "tokenizer.model",
                "tokenizer_config.json"
            ]
            
            for file in required_files:
                file_path = os.path.join(self.model_path, file)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Required file not found: {file_path}")
            
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, 
                use_fast=True,
                local_files_only=True
            )
            
            logger.info("Loading model...")
            # Check for safetensors or pytorch files
            model_files = os.listdir(self.model_path)
            has_safetensors = any(f.endswith(".safetensors") for f in model_files)
            has_pytorch_bin = any(f.startswith("pytorch_model") and f.endswith(".bin") for f in model_files)
            
            if not (has_safetensors or has_pytorch_bin):
                raise ValueError("No model weights found (safetensors or pytorch bin files)")
            
            load_args = {
                "pretrained_model_name_or_path": self.model_path,
                "device_map": "auto",
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "low_cpu_mem_usage": True,
                "local_files_only": True
            }
            
            if self.device == "cuda":
                load_args["load_in_4bit"] = True
                load_args["bnb_4bit_compute_dtype"] = torch.float16
            
            self.model = AutoModelForCausalLM.from_pretrained(**load_args)
            logger.info("Model loaded successfully.")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def generate_response(self, prompt, max_length=200):
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_length,
                do_sample=True,
                temperature=0.85,
                top_p=0.92,
                repetition_penalty=1.15,
                pad_token_id=self.tokenizer.eos_token_id
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract only the new response
            return response.split(prompt)[-1].strip()
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error. Please try again."
    
    def stream_response(self, prompt, max_length=200):
        """Stream response token by token"""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        # Create streamer
        streamer = TextIteratorStreamer(
            self.tokenizer, 
            skip_prompt=True, 
            timeout=20.0, 
            skip_special_tokens=True
        )
        
        # Generation parameters
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_length,
            do_sample=True,
            temperature=0.85,
            top_p=0.92,
            repetition_penalty=1.15,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Start generation in a separate thread
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        # Yield tokens as they come
        for new_token in streamer:
            if new_token:
                yield new_token