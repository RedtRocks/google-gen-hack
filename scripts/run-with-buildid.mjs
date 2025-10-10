import { spawn } from 'node:child_process';

const buildId = Date.now().toString();
const [command, ...args] = process.argv.slice(2);

if (!command) {
  console.error('Usage: node scripts/run-with-buildid.mjs <command> [args...]');
  process.exit(1);
}

const child = spawn(command, args, {
  stdio: 'inherit',
  shell: true,
  env: {
    ...process.env,
    VITE_MAKYO_BUILDID: buildId,
  },
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
