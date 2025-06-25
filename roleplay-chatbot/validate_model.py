import os
from transformers import AutoConfig

model_path = "./models/pygmalion-2-7b"

try:
    print(f"Validating model at: {model_path}")
    
    # Check if directory exists
    if not os.path.exists(model_path):
        raise FileNotFoundError("Model directory not found")
    
    # Check for required files
    required_files = [
        "config.json", 
        "tokenizer.json", 
        "tokenizer.model",
        "tokenizer_config.json"
    ]
    
    for file in required_files:
        path = os.path.join(model_path, file)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing file: {file}")
        print(f"Found: {file}")
    
    # Try to load config
    config = AutoConfig.from_pretrained(model_path, local_files_only=True)
    print("Config loaded successfully!")
    print(f"Model type: {config.model_type}")
    
    # Check for model weights
    weight_files = [
        f for f in os.listdir(model_path) 
        if f.endswith(".safetensors") or f.startswith("pytorch_model")
    ]
    
    if not weight_files:
        raise ValueError("No model weight files found")
    
    print("Found weight files:")
    for file in weight_files:
        print(f"- {file}")
    
    print("\nModel validation successful! You can now run app.py")
    
except Exception as e:
    print(f"\nValidation failed: {e}")
    print("Please check your model files and directory structure")