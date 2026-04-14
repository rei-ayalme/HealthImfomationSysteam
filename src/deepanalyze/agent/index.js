import 'dotenv/config';

let initialized = false;

export async function bootstrapAgent() {
  if (initialized) return;

  const provider = process.env.DA_AGENT_PROVIDER || 'openai';
  if (provider === 'openai' && process.env.DA_OPENAI_API_KEY && process.env.DA_OPENAI_API_KEY.trim()) {
    initialized = true;
    return;
  }

  initialized = true;
}
