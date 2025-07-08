const express = require("express");
const fs      = require("fs");
const path    = require("path");

const app = express();
app.use(express.json());

const BUF_DIR = path.join(__dirname, "toSendData/buffer");
if (!fs.existsSync(BUF_DIR)) fs.mkdirSync(BUF_DIR);

app.post("/api/data", (req, res) => {
    const now = new Date().toISOString();
    console.log(`[${now}] Received data via POST.`);
    console.log("Request Body:", req.body);

    // scrivi un file unico per ogni lettura
    const filename = `reading-${Date.now()}.json`;
    fs.writeFileSync(
        path.join(BUF_DIR, filename),
        JSON.stringify(req.body),
        "utf8"
    );

    res.sendStatus(200);
});

app.listen(3000, () => {
    console.log("Listening on port 3000");
});