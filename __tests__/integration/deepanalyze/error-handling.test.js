import request from 'supertest';
import { createDeepAnalyzeApp } from '../../../deepanalyze/app.js';

describe('deepanalyze error handling', () => {
  test('非法 payload 返回 400 且包含 error.code，进程未崩溃', async () => {
    const app = createDeepAnalyzeApp();
    const res = await request(app).post('/api/analyze').send({ invalid: true });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error.code');
    expect(process.exitCode || 0).toBe(0);
  });
});
