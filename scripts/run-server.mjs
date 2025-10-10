import { spawn } from 'node:child_process';

const env = {
  ...process.env,
  MAKYO_API_TOKEN: process.env.MAKYO_API_TOKEN ?? 'testtoken',
  MAKYO_FRONTEND_FILES_PATH: process.env.MAKYO_FRONTEND_FILES_PATH ?? 'client/dist',
};

const child = spawn('npx', ['tsx', 'watch', 'server/index.ts'], {
  stdio: 'inherit',
  shell: true,
  env,
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
