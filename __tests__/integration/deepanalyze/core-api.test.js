import request from 'supertest';
import { createDeepAnalyzeApp } from '../../../deepanalyze/app.js';

describe('deepanalyze core api', () => {
  test('/api/analyze 返回 expectedKeys', async () => {
    const app = createDeepAnalyzeApp();
    const res = await request(app).post('/api/analyze').send({ text: '分析这段样例文本' });
    expect(res.status).toBe(200);
    const expectedKeys = ['summary', 'score', 'details'];
    expectedKeys.forEach((k) => expect(res.body).toHaveProperty(k));
  });
});
