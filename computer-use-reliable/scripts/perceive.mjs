#!/usr/bin/env node
/**
 * perceive.mjs - turn a window screenshot into structured UI data.
 *
 * Modes:
 *   --info <image>                     print image dimensions
 *   --find-color R,G,B [opts] <image>  connected components of similar color
 *   --list-colors [opts] <image>       dominant quantized colors
 *   --ocr [langs] [opts] <image>       OCR words with bounding boxes
 *
 * Options:
 *   --tolerance N       color distance tolerance (default 40)
 *   --region x,y,w,h    limit analysis to a region (window coords)
 *   --min-pixels N      drop components smaller than N pixels (default 20)
 *   --max-items N       limit returned items (default 20)
 *   --tessdata <dir>    OCR language data cache dir (default %LOCALAPPDATA%/computer-use-reliable/tessdata)
 *   --no-download       fail OCR instead of downloading missing language data
 *
 * Output: JSON { width, height, items: [{ type, text?, x, y, width, height, centerX, centerY, count? }] }
 * Coordinates are screenshot pixels = window-relative pixels for sky.click.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VALUE_FLAGS = new Set(["find-color", "ocr", "tolerance", "region", "min-pixels", "max-items", "tessdata"]);

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

function findNodeModulesDir() {
  const candidates = [];
  if (process.env.NODE_MODULES_DIR) candidates.push(process.env.NODE_MODULES_DIR);
  candidates.push(path.join(__dirname, "..", "node_modules"));
  const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
  const runtimesRoot = path.join(localAppData, "OpenAI", "Codex", "runtimes", "cua_node");
  if (existsSync(runtimesRoot)) {
    const versions = [];
    for (const v of readdirSync(runtimesRoot)) {
      const p = path.join(runtimesRoot, v, "bin", "node_modules");
      if (existsSync(p)) versions.push(p);
    }
    versions.sort();
    candidates.push(...versions);
  }
  for (const c of candidates) {
    if (c && existsSync(path.join(c, "jpeg-js"))) return c;
  }
  return null;
}

async function loadPkg(pkg, entry = "index.js") {
  const dir = findNodeModulesDir();
  if (!dir) throw new Error(`Cannot find node_modules with ${pkg}. Set NODE_MODULES_DIR.`);
  return import(pathToFileURL(path.join(dir, pkg, entry)).href);
}

function decodeImage(file) {
  const buf = readFileSync(file);
  if (buf[0] === 0xff && buf[1] === 0xd8) return decodeJpeg(buf);
  if (buf[0] === 0x89 && buf[1] === 0x50) return decodePng(buf);
  throw new Error(`Unsupported image format for ${file} (expected JPEG or PNG)`);
}

async function decodeJpeg(buf) {
  const jpeg = await loadPkg("jpeg-js");
  const d = jpeg.decode(buf, { useTArray: true });
  return { width: d.width, height: d.height, data: d.data };
}

async function decodePng(buf) {
  const png = await loadPkg("pngjs", "lib/png.js");
  const d = png.PNG.sync.read(buf);
  return { width: d.width, height: d.height, data: d.data };
}

function regionOf(opts, width, height) {
  const r = opts.region;
  if (!r) return { x: 0, y: 0, w: width, h: height };
  let [x, y, w, h] = r.split(",").map(Number);
  if ([x, y, w, h].some((v) => !Number.isFinite(v))) throw new Error(`Bad region: ${r}`);
  x = Math.max(0, Math.min(x, width - 1));
  y = Math.max(0, Math.min(y, height - 1));
  w = Math.min(w, width - x);
  h = Math.min(h, height - y);
  return { x, y, w, h };
}

function parseColor(s) {
  const [r, g, b] = s.split(",").map(Number);
  if ([r, g, b].some((v) => !Number.isFinite(v))) throw new Error(`Bad color: ${s}`);
  return { r, g, b };
}

function colorDist(c1, c2) {
  return Math.sqrt((c1.r - c2.r) ** 2 + (c1.g - c2.g) ** 2 + (c1.b - c2.b) ** 2);
}

function findColor(img, target, tolerance, region, minPixels, maxItems) {
  const { width, height, data } = img;
  const seen = new Uint8Array(width * height);
  const items = [];
  for (let y = region.y; y < region.y + region.h; y++) {
    for (let x = region.x; x < region.x + region.w; x++) {
      const idx = y * width + x;
      if (seen[idx]) continue;
      const i = idx * 4;
      const c = { r: data[i], g: data[i + 1], b: data[i + 2] };
      if (colorDist(c, target) > tolerance) continue;
      // Flood fill component.
      const stack = [idx];
      seen[idx] = 1;
      let minX = x, maxX = x, minY = y, maxY = y, count = 0;
      while (stack.length) {
        const cur = stack.pop();
        const cx = cur % width;
        const cy = (cur - cx) / width;
        count++;
        if (cx < minX) minX = cx;
        if (cx > maxX) maxX = cx;
        if (cy < minY) minY = cy;
        if (cy > maxY) maxY = cy;
        const neighbors = [
          cx > region.x ? cur - 1 : -1,
          cx < region.x + region.w - 1 ? cur + 1 : -1,
          cy > region.y ? cur - width : -1,
          cy < region.y + region.h - 1 ? cur + width : -1,
        ];
        for (const n of neighbors) {
          if (n < 0 || seen[n]) continue;
          const ni = n * 4;
          const nc = { r: data[ni], g: data[ni + 1], b: data[ni + 2] };
          if (colorDist(nc, target) <= tolerance) {
            seen[n] = 1;
            stack.push(n);
          }
        }
      }
      if (count >= minPixels) {
        items.push({
          type: "color",
          x: minX,
          y: minY,
          width: maxX - minX + 1,
          height: maxY - minY + 1,
          centerX: Math.round((minX + maxX) / 2),
          centerY: Math.round((minY + maxY) / 2),
          count,
        });
      }
    }
  }
  items.sort((a, b) => b.count - a.count);
  return items.slice(0, maxItems);
}

function listColors(img, region, maxItems) {
  const { width, height, data } = img;
  const counts = new Map();
  for (let y = region.y; y < region.y + region.h; y += 2) {
    for (let x = region.x; x < region.x + region.w; x += 2) {
      const i = (y * width + x) * 4;
      const key = `${Math.round(data[i] / 32) * 32},${Math.round(data[i + 1] / 32) * 32},${Math.round(data[i + 2] / 32) * 32}`;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxItems)
    .map(([color, count]) => ({ type: "color", color, count }));
}

async function ensureTessdata(langs, tessdataDir, noDownload) {
  mkdirSync(tessdataDir, { recursive: true });
  for (const lang of langs) {
    const file = path.join(tessdataDir, `${lang}.traineddata.gz`);
    if (existsSync(file)) continue;
    if (noDownload) throw new Error(`Missing language data ${file}; re-run without --no-download or download it manually`);
    const urls = [
      `https://cdn.jsdelivr.net/npm/@tesseract.js-data/${lang}/4.0.0_best_int/${lang}.traineddata.gz`,
      `https://tessdata.projectnaptha.com/4.0.0/${lang}.traineddata.gz`,
    ];
    let ok = false;
    for (const url of urls) {
      try {
        const res = await fetch(url);
        if (!res.ok) continue;
        const buf = Buffer.from(await res.arrayBuffer());
        writeFileSync(file, buf);
        ok = true;
        break;
      } catch {
        /* try next */
      }
    }
    if (!ok) throw new Error(`Failed to download language data for ${lang} (network required)`);
  }
}

async function runOcr(img, langs, tessdataDir, region, noDownload) {
  const langList = langs.split("+").map((s) => s.trim()).filter(Boolean);
  await ensureTessdata(langList, tessdataDir, noDownload);
  const tesseract = await loadPkg("tesseract.js", "src/index.js");
  const worker = await tesseract.createWorker(langList.join("+"), 1, {
    langPath: tessdataDir,
    cachePath: tessdataDir,
    cacheMethod: "writeOnly",
    gzip: true,
  });
  const { data } = await worker.recognize(img.file, {}, { tsv: true, text: false });
  await worker.terminate();
  const words = [];
  if (typeof data.tsv === "string") {
    const rows = data.tsv.split("\n");
    for (let i = 1; i < rows.length; i++) {
      const cols = rows[i].split("\t");
      if (cols.length < 12 || Number(cols[0]) !== 5) continue;
      const text = cols[11];
      if (!text || !text.trim()) continue;
      const left = Number(cols[6]);
      const top = Number(cols[7]);
      const w = Number(cols[8]);
      const h = Number(cols[9]);
      const cx = Math.round(left + w / 2);
      const cy = Math.round(top + h / 2);
      if (cx < region.x || cx >= region.x + region.w || cy < region.y || cy >= region.y + region.h) continue;
      words.push({
        type: "ocr",
        text,
        x: left,
        y: top,
        width: w,
        height: h,
        centerX: cx,
        centerY: cy,
        confidence: Number(cols[10]),
      });
    }
  }
  return words;
}

function help() {
  console.log(`perceive.mjs - screenshot perception for Computer Use

Usage:
  node perceive.mjs --info <image>
  node perceive.mjs --find-color R,G,B [--tolerance 40] [--region x,y,w,h] [--min-pixels 20] [--max-items 20] <image>
  node perceive.mjs --list-colors [--region x,y,w,h] [--max-items 20] <image>
  node perceive.mjs --ocr eng+chi_sim [--region x,y,w,h] [--tessdata <dir>] <image>

Output is JSON. Coordinates are screenshot pixels (= window-relative for sky.click).`);
}

const args = parseArgs(process.argv.slice(2));
const mode = Object.keys(args.opts).find((k) => ["info", "find-color", "list-colors", "ocr", "help"].includes(k));

if (mode === "help" || !mode) {
  help();
  process.exit(mode ? 0 : 1);
}

const imageFile = args.positionals[args.positionals.length - 1];
if (!imageFile) {
  console.error(JSON.stringify({ error: "missing image path" }));
  process.exit(1);
}

try {
  const img = await decodeImage(imageFile);
  img.file = imageFile;
  const region = regionOf(args.opts, img.width, img.height);
  const maxItems = Number(args.opts["max-items"] ?? 20);
  let items = [];

  if (mode === "info") {
    console.log(JSON.stringify({ width: img.width, height: img.height }));
    process.exit(0);
  }
  if (mode === "find-color") {
    const target = parseColor(args.opts["find-color"]);
    const tolerance = Number(args.opts.tolerance ?? 40);
    const minPixels = Number(args.opts["min-pixels"] ?? 20);
    items = findColor(img, target, tolerance, region, minPixels, maxItems);
  } else if (mode === "list-colors") {
    items = listColors(img, region, maxItems);
  } else if (mode === "ocr") {
    const langs = String(args.opts.ocr ?? "eng");
    const tessdataDir = path.resolve(args.opts.tessdata ?? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"), "computer-use-reliable", "tessdata"));
    items = await runOcr(img, langs, tessdataDir, region, Boolean(args.opts["no-download"]));
  }

  console.log(JSON.stringify({ width: img.width, height: img.height, items }, null, 2));
} catch (e) {
  console.error(JSON.stringify({ error: String(e?.message ?? e), stack: String(e?.stack ?? "") }));
  process.exit(1);
}
