**Step 1**

1 Install Python 3.12.**

2 Install git

3 Install git lfs 

# For Ubuntu/Debian
sudo apt-get install git-lfs

# For Windows
Download from https://git-lfs.github.com/

**Step 2**

Run pip install -r requirements.txt

**Step 3**

git lfs install

cd models
run git clone https://huggingface.co/PygmalionAI/pygmalion-2-7b

# Linux/Mac

mkdir -p models/pygmalion-7b

cd models/pygmalion-7b

**Step 4** 

# Enable long paths (PowerShell)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -Type DWord

# Install build tools (PowerShell)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121


**Step 5**

Run **python app.py** in cmd from the directory. 

**Additional Note**

# In model_handler.py __init__ method (GPU 8GB or More)
if self.device == "cuda":
    self.model = AutoModelForCausalLM.from_pretrained(
        self.model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,  # 4-bit quantization
        bnb_4bit_compute_dtype=torch.float16,
        low_cpu_mem_usage=True
    )

# In model_handler.py __init__ method (CPU Only)
self.model = AutoModelForCausalLM.from_pretrained(
    self.model_path,
    torch_dtype=torch.float32,
    device_map="auto"
)

# Reduce VRAM usage by adding to model_handler.py:
self.model = AutoModelForCausalLM.from_pretrained(
    self.model_path,
    load_in_8bit=True,  # Use 8-bit instead of 4-bit
    device_map="auto"
)

# To Add More conversation memory: (Current Value 8)
# In app.py chat endpoint
session['chat_history'] = history[-10:]  # Keep only last 10 messages


**Troubleshooting Tips**
# If you get out-of-memory errors:
Reduce MAX_RESPONSE_LENGTH in config.py
Use load_in_8bit=True instead of 4-bit in model_handler.py
# For faster responses:
Reduce MAX_RESPONSE_LENGTH
Lower temperature in generation parameters
# If streaming doesn't work:
Disable streaming in config.py
Check browser console for errors

**# Model Execution Architecture**
┌─────────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│                     │       │                  │       │                  │
│   Web Browser       ├──────►│   Flask Server   ├──────►│   Local AI Model │
│   (User Interface)  │ HTTP  │   (Python)       │ Python│   (Pygmalion-7B) │
│                     │◄──────┤                  │◄──────┤                  │
└─────────────────────┘       └──────────────────┘       └──────────────────┘
