
// server.js
const express = require("express");
const fs      = require("fs");
const path    = require("path");

const app = express();
app.use(express.json());

const BUF_DIR = path.join(__dirname, "toSendData/buffer");
if (!fs.existsSync(BUF_DIR)) fs.mkdirSync(BUF_DIR);

let segmentCounter = 0;

app.post("/api/data", (req, res) => {
  const now = new Date().toISOString();
  const samples = Array.isArray(req.body.samples)
    ? req.body.samples
    : [req.body];

  console.log(`[${now}] Received ${samples.length} samples.`);

  // Crea un singolo file che contiene TUTTI i samples arrivati in questo POST
  const filename = `segment${segmentCounter++}_raw.json`;
  const fullPath = path.join(BUF_DIR, filename);
  const payload  = JSON.stringify({ samples }, null, 0);

  fs.writeFile(fullPath, payload, "utf8", err => {
    if (err) {
      console.error(`Error writing ${filename}:`, err);
      return res.sendStatus(500);
    }
    console.log(`→ Saved ${samples.length} samples to ${filename}`);
    res.sendStatus(200);
  });
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Listening on port ${PORT}`);
});
