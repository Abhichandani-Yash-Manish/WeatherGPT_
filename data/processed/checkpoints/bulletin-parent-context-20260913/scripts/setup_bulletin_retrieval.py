"""Install the pinned public embedding snapshot after installing requirements-bulletins.txt."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from huggingface_hub import snapshot_download
from weathergpt_data.bulletin_index import MODEL,REVISION,embed
path=snapshot_download(MODEL,revision=REVISION,token=False,allow_patterns=['*.json','*.safetensors','sentencepiece.bpe.model','README.md','1_Pooling/*'],ignore_patterns=['onnx/*','openvino/*'])
print(json.dumps({'model':MODEL,'revision':REVISION,'local_path':path,'embedding_dimensions':len(embed(['weather advisory'])[0]),'remote_code':False}))
