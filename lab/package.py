"""Export source with an explicit whitelist; never walk the runtime data directory."""
import argparse
import json
import subprocess
import zipfile
from .common import ROOT,DATA
from .store import Store
from .reports import export_zip

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run',action='append',default=[]); args=parser.parse_args()
    target=DATA/'deliverables'; target.mkdir(parents=True,exist_ok=True)
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    exact={'README.md','CHANGELOG.md','AGENTS.md','.gitignore','package.json','pnpm-lock.yaml','server.mjs',
           'lab-proxy.mjs','vite.config.js','tsconfig.lab.json','index.html','.env.example'}
    roots=('lab/','src/','tests/','docs/','.github/','scripts/')
    suffixes={'.py','.md','.json','.lock','.in','.html','.ts','.js','.mjs','.css','.yml','.yaml','.svg','.txt'}
    output=target/'anywear-lab-v0.1-source.zip'; included=[]
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name in names:
            if not name: continue
            p=ROOT/name
            if name not in exact and not (name.startswith(roots) and p.suffix in suffixes): continue
            if 'local-products/' in name or '__pycache__' in name or not p.is_file(): continue
            z.write(p,'anywear-lab/'+name); included.append(name)
        z.writestr('anywear-lab/EXPORT_MANIFEST.json',json.dumps({'files':included,'runtime_data_included':False},indent=2))
    for run in args.run: (target/f'{run}-report.zip').write_bytes(export_zip(Store(),run))
    print(output)

if __name__=='__main__': main()
