import {spawnSync} from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const python=path.join(root,'.venv','bin','python');
if(!fs.existsSync(python)){
  console.error('请先按 lab/README.md 安装 Python 3.12 环境。 Set up Python 3.12 using lab/README.md.');process.exit(1);
}
const args=process.argv.slice(2);
const moduleName=args[0]==='doctor'?'lab.doctor':args[0]==='package'?'lab.package':'lab.manage';
const result=spawnSync(python,['-m',moduleName,...(moduleName==='lab.manage'?args:args.slice(1))],
  {cwd:root,stdio:'inherit',env:{...process.env,ANYWEAR_NODE:process.execPath}});
process.exit(result.status??1);
