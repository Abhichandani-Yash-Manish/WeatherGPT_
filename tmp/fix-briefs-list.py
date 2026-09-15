import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
text = p.read_text()
old = "                            'sources':entry['sources'],'status':entry['status'],'evidence':entry['evidence'],"
assert text.count(old) == 1
text = text.replace(old, "                            'sources':entry['sources'],'status':entry['payload'].get('status'),'evidence':entry['evidence'],", 1)
p.write_text(text)
d = pathlib.Path('tmp/evidence-personas-briefcase.py')
dt = d.read_text()
old_tail = "    finally:\n        server.terminate()"
assert dt.count(old_tail) == 1
dt = dt.replace(old_tail, "    except Exception as failure:\n        server.terminate()\n        try:\n            server.wait(timeout=10)\n        except subprocess.TimeoutExpired:\n            server.kill()\n        print('--- server output ---')\n        print(server.stdout.read().decode('utf-8', 'replace')[-3000:])\n        raise\n    finally:\n        server.terminate()", 1)
d.write_text(dt)
print('patched')
