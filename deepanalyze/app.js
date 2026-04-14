import express from 'express';

export function createDeepAnalyzeApp() {
  const app = express();
  app.use(express.json({ limit: '1mb' }));

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/api/analyze', (req, res) => {
    const { text, data } = req.body || {};
    const payload = typeof text === 'string' ? text.trim() : '';

    if (!payload && (typeof data !== 'object' || data === null)) {
      res.status(400).json({
        error: {
          code: 'INVALID_PAYLOAD',
          message: 'text 或 data 至少提供一个有效字段'
        }
      });
      return;
    }

    const detailSource = payload || JSON.stringify(data);
    const score = Math.min(100, Math.max(0, Math.round(Math.min(detailSource.length, 100))));

    res.status(200).json({
      summary: `已完成分析，输入长度 ${detailSource.length}`,
      score,
      details: {
        model: process.env.DA_MODEL || 'deepanalyze-8b',
        timestamp: Date.now(),
        inputType: payload ? 'text' : 'json'
      }
    });
  });

  return app;
}
