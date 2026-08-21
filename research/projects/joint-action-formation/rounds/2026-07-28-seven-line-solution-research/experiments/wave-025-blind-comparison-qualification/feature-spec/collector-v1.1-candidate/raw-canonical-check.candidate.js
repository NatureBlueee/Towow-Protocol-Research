#!/usr/bin/env node
"use strict";

// Duplicate member detection is performed before this helper by the Python
// admission layer.  This helper owns exact compatibility with the producer's
// JavaScript JSON.stringify number/string rendering and recursive key order.

const fs = require("node:fs");

function canonicalize(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("non-finite number");
    return value;
  }
  if (Array.isArray(value)) return value.map(canonicalize);
  if (typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) result[key] = canonicalize(value[key]);
    return result;
  }
  throw new TypeError(`unsupported JSON type ${typeof value}`);
}

function main() {
  if (process.argv.length !== 3) return 64;
  const raw = fs.readFileSync(process.argv[2]);
  const text = raw.toString("utf8");
  const parsed = JSON.parse(text);
  const expected = Buffer.from(`${JSON.stringify(canonicalize(parsed))}\n`, "utf8");
  if (!raw.equals(expected)) {
    process.stderr.write("raw bytes are not recursive-key-sorted compact JSON plus exactly one LF\n");
    return 1;
  }
  return 0;
}

process.exitCode = main();
