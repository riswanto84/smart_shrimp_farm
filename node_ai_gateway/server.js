import "dotenv/config";
import express from "express";
import helmet from "helmet";

const app = express();
const host = process.env.HOST || "0.0.0.0";
const port = Number(process.env.PORT || 3000);
const ollamaUrl = (process.env.OLLAMA_BASE_URL || "http://127.0.0.1:11434").replace(/\/$/, "");
const defaultModel = process.env.OLLAMA_MODEL || "llama3.1:8b";
const apiKey = process.env.AI_GATEWAY_API_KEY || "";

app.use(helmet());
app.use(express.json({ limit: "1mb" }));

function authorize(req, res, next) {
  if (!apiKey || req.get("X-AI-Gateway-Key") !== apiKey) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

app.get("/health", authorize, async (_req, res) => {
  try {
    const response = await fetch(`${ollamaUrl}/api/tags`, { signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error(`Ollama HTTP ${response.status}`);
    const payload = await response.json();
    return res.json({
      status: "online",
      gateway: "online",
      ollama: "online",
      model: defaultModel,
      available_models: (payload.models || []).map((m) => m.name),
    });
  } catch (error) {
    return res.status(503).json({ status: "offline", gateway: "online", ollama: "offline", error: error.message });
  }
});

app.post("/api/chat", authorize, async (req, res) => {
  const messages = Array.isArray(req.body.messages) ? req.body.messages : [];
  const model = req.body.model || defaultModel;
  if (!messages.length) return res.status(400).json({ error: "messages tidak boleh kosong" });

  try {
    const response = await fetch(`${ollamaUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages, stream: false, think: false }),
      signal: AbortSignal.timeout(300000),
    });
    if (!response.ok) throw new Error(await response.text());
    const payload = await response.json();
    return res.json({ message: payload.message?.content || "", model, metrics: {
      total_duration: payload.total_duration || null,
      eval_count: payload.eval_count || null
    }});
  } catch (error) {
    return res.status(502).json({ error: "Ollama gagal merespons", detail: error.message });
  }
});

app.listen(port, host, () => console.log(`Smart Shrimp AI Gateway aktif di http://${host}:${port}`));
