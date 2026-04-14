import { spawn } from 'node:child_process';

function waitForReady(proc, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let logs = '';
    const timer = setInterval(() => {
      if (Date.now() - start > timeoutMs) {
        clearInterval(timer);
        reject(new Error(`服务启动超时: ${logs}`));
      }
    }, 200);

    proc.stdout.on('data', (buf) => {
      logs += buf.toString();
      if (logs.includes('Listening on http://0.0.0.0:3100')) {
        clearInterval(timer);
        resolve();
      }
    });

    proc.stderr.on('data', (buf) => {
      logs += buf.toString();
    });

    proc.on('exit', (code) => {
      clearInterval(timer);
      reject(new Error(`服务提前退出 code=${code}: ${logs}`));
    });
  });
}

describe('deepanalyze init', () => {
  test('npm start 能在 30 秒内启动且 /health 返回 200', async () => {
    const proc = spawn('npm start', {
      cwd: process.cwd(),
      env: { ...process.env, DA_PORT: '3100', DA_HOST: '0.0.0.0', DA_LOG_LEVEL: 'info' },
      shell: true
    });
    try {
      await waitForReady(proc, 30000);
      const res = await fetch('http://127.0.0.1:3100/health');
      expect(res.status).toBe(200);
      const json = await res.json();
      expect(json.status).toBe('ok');
    } finally {
      proc.kill();
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }, 35000);
});
