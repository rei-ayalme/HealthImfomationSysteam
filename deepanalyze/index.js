import 'dotenv/config';
import { createDeepAnalyzeApp } from './app.js';
import { bootstrapAgent } from '../src/deepanalyze/agent/index.js';

const host = process.env.DA_HOST || '0.0.0.0';
const port = Number(process.env.DA_PORT || 3000);
const logLevel = (process.env.DA_LOG_LEVEL || 'info').toLowerCase();

bootstrapAgent().catch((e) => {
  console.error('Agent init failed', e);
  process.exit(1);
});

const app = createDeepAnalyzeApp();
app.listen(port, host, () => {
  if (logLevel !== 'silent') {
    console.log(`Listening on http://${host}:${port}`);
  }
});
