import {defineConfig} from 'vite';
import path from 'node:path';
export default defineConfig({
  build:{rollupOptions:{input:{fitting:path.resolve('index.html'),lab:path.resolve('lab/index.html')}}},
  server:{proxy:{'/api/lab':{target:'http://127.0.0.1:8001'}}},
});
