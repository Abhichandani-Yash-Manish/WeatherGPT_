"""Start the local chat workspace, starting installed Ollama if necessary."""
import json,os,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def available():
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as response:return json.load(response).get('models',[])
    except OSError:return None

models=available()
if models is None:
    binary=shutil.which('ollama')
    if not binary:raise SystemExit('Ollama is not on PATH. Install/start Ollama, then run this command again.')
    log=ROOT/'data/runtime/conversation/ollama-server.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('ab') as output:subprocess.Popen([binary,'serve'],stdout=output,stderr=output,start_new_session=True)
    for _ in range(20):
        time.sleep(.5);models=available()
        if models is not None:break
    if models is None:raise SystemExit('Ollama did not become available. Check data/runtime/conversation/ollama-server.log.')
model=os.getenv('WEATHERGPT_MODEL','qwen3.6:latest')
if not any(m.get('name')==model for m in models):raise SystemExit('The selected model is not installed: '+model+'. Set WEATHERGPT_MODEL to an installed model or pull it with Ollama.')
os.chdir(ROOT)
os.execv(sys.executable,[sys.executable,'-m','weathergpt_data.workspace',*sys.argv[1:]])
