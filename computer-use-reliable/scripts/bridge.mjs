#!/usr/bin/env node
/**
 * bridge.mjs - fallback bridge to the Computer Use node_repl runtime.
 *
 * Use only when the `node_repl` tool is NOT exposed in the current session.
 * It spawns the bundled `node_repl.exe` (MCP stdio server), sends one `js`
 * execution, auto-answers "Allow Codex to use <app>?" approval prompts, saves
 * emitted images, and prints a JSON result.
 *
 * Usage:
 *   node bridge.mjs <base64-encoded-javascript>
 *   node bridge.mjs --file cell.js
 *   node bridge.mjs --file cell.js --timeout-ms 120000 --log-all
 *   node bridge.mjs --file cell.js --no-auto-approve   # fail on approval prompts
 *   node bridge.mjs --file cell.js --exe <path-to-node_repl.exe>
 *
 * Because each call is a fresh kernel, each cell must be self-contained:
 * re-import @oai/sky, re-select the target window, and act + verify in one cell.
 */

import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { writeFileSync, mkdirSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const VALUE_FLAGS = new Set(["file", "timeout-ms", "exe", "out-dir"]);

function parseArgs(argv) {
  const out = { positionals: [], opts: {} };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const eq = a.indexOf("=");
      const key = eq >= 0 ? a.slice(2, eq) : a.slice(2);
      if (eq >= 0) {
        out.opts[key] = a.slice(eq + 1);
      } else if (VALUE_FLAGS.has(key)) {
        out.opts[key] = argv[++i] ?? true;
      } else {
        out.opts[key] = true;
      }
    } else {
      out.positionals.push(a);
    }
  }
  return out;
}

function discoverNodeRepl() {
  if (process.env.NODE_REPL_EXE && existsSync(process.env.NODE_REPL_EXE)) return process.env.NODE_REPL_EXE;
  const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
  const runtimesRoot = path.join(localAppData, "OpenAI", "Codex", "runtimes", "cua_node");
  if (existsSync(runtimesRoot)) {
    const versions = readdirSync(runtimesRoot).sort();
    for (let i = versions.length - 1; i >= 0; i--) {
      const exe = path.join(runtimesRoot, versions[i], "bin", "node_repl.exe");
      if (existsSync(exe)) return exe;
    }
  }
  return null;
}

function help() {
  console.log(`bridge.mjs - fallback bridge to the Computer Use node_repl runtime

Usage:
  node bridge.mjs <base64-encoded-javascript>
  node bridge.mjs --file cell.js [--timeout-ms N] [--log-all] [--no-auto-approve] [--exe <path>] [--out-dir <dir>]

The cell runs in a fresh kernel and must be self-contained (re-import @oai/sky,
re-select the window, act + verify). Output is JSON:
  { isError, texts, savedImages } or { error }`);
}

const args = parseArgs(process.argv.slice(2));
if (args.opts.help || (!args.opts.file && args.positionals.length === 0)) {
  help();
  process.exit(args.opts.help ? 0 : 1);
}

const exe = args.opts.exe || discoverNodeRepl();
if (!exe) {
  console.error(JSON.stringify({ error: "node_repl.exe not found; pass --exe <path> or set NODE_REPL_EXE" }));
  process.exit(1);
}

let code;
if (args.opts.file) {
  const { readFileSync } = await import("node:fs");
  code = readFileSync(path.resolve(args.opts.file), "utf8");
} else {
  code = Buffer.from(args.positionals[0], "base64").toString("utf8");
}

const timeoutMs = Number(args.opts["timeout-ms"] ?? 30000);
const outDir = path.resolve(args.opts["out-dir"] ?? "screenshots");
const autoApprove = !args.opts["no-auto-approve"];
const logAll = Boolean(args.opts["log-all"]);

const child = spawn(exe, [], { stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
let nextId = 0;
const pending = new Map();
const rl = createInterface({ input: child.stdout });

rl.on("line", (line) => {
  if (logAll) console.error("RX " + line.slice(0, 4000));
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    return;
  }
  if (msg.method != null && msg.id != null) {
    // Server -> client request (approval prompts).
    if (logAll) console.error("REQ " + JSON.stringify(msg).slice(0, 2000));
    if (/elicitation/i.test(msg.method)) {
      const result = autoApprove
        ? { action: "accept", content: null, _meta: { persist: "session" } }
        : { action: "decline", content: null, _meta: {} };
      const reply = { jsonrpc: "2.0", id: msg.id, result };
      child.stdin.write(JSON.stringify(reply) + "\n");
      if (logAll) console.error("APPROVAL " + (autoApprove ? "ACCEPTED" : "DECLINED") + " " + JSON.stringify(reply));
    } else {
      child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "method not found" } }) + "\n");
    }
    return;
  }
  if (msg.id == null) {
    if (logAll) console.error("NOTIFY " + JSON.stringify(msg).slice(0, 4000));
    return;
  }
  if (pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(JSON.stringify(msg.error)));
    else resolve(msg.result);
  }
});

function request(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
}

function notify(method, params = {}) {
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n");
}

const timeout = setTimeout(() => {
  console.error(JSON.stringify({ error: `bridge timed out after ${timeoutMs}ms` }));
  child.kill();
  process.exit(1);
}, timeoutMs + 5000);

try {
  await request("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: { elicitation: {} },
    clientInfo: { name: "computer-use-reliable-bridge", version: "1.0.0" },
  });
  notify("notifications/initialized");

  const result = await request("tools/call", {
    name: "js",
    arguments: { code, title: "computer-use-reliable cell" },
  });

  const texts = (result.content ?? [])
    .filter((c) => c.type === "text")
    .map((c) => c.text)
    .join("\n");
  const images = (result.content ?? []).filter((c) => c.type === "image");
  const savedImages = [];
  mkdirSync(outDir, { recursive: true });
  for (let i = 0; i < images.length; i++) {
    const img = images[i];
    const data = img.data ?? img.image;
    let buffer;
    if (typeof data === "string") buffer = Buffer.from(data.split(",")[1] ?? data, "base64");
    else if (data && typeof data === "object" && "bytes" in data) buffer = Buffer.from(data.bytes);
    else if (data && data.type === "Buffer" && Array.isArray(data.data)) buffer = Buffer.from(data.data);
    if (buffer) {
      const file = path.join(outDir, `${Date.now()}_${i}.png`);
      writeFileSync(file, buffer);
      savedImages.push(file);
    }
  }
  console.log(JSON.stringify({ isError: result.isError, texts, savedImages }));
} catch (error) {
  console.log(JSON.stringify({ error: String(error?.message ?? error), stack: String(error?.stack ?? "") }));
} finally {
  clearTimeout(timeout);
  child.kill();
  process.exit(0);
}
