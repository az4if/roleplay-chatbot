from huggingface_hub import snapshot_download
import shutil
import os

MODEL_ID = "PygmalionAI/pygmalion-2-7b"
LOCAL_PATH = "./models/pygmalion-2-7b"

# Download model
snapshot_download(
    repo_id=MODEL_ID,
    local_dir=LOCAL_PATH,
    local_dir_use_symlinks=False,
    revision="main",
    ignore_patterns=["*.h5", "*.ot", "*.msgpack"],
    allow_patterns=["*.json", "*.model", "*.safetensors", "*.py", "*.txt", "*.bin"]
)

print(f"Model downloaded to {LOCAL_PATH}")