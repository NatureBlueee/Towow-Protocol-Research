#!/usr/bin/env node
"use strict";

// This process is intentionally observational. It never calls a lawful
// Authority/Target API and it has no network dependency. The host runner owns
// isolation; this file only records candidate-visible surfaces.

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const INPUT_SCHEMA = "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1";
const OUTPUT_SCHEMA = "WAVE025_LEAK_ONLY_FEATURES_V1";
const FAILURE_SCHEMA = "WAVE025_LEAK_ONLY_COLLECTOR_FAILURE_V1";
const COLLECTOR_VERSION = "1.0.0";
const MAX_TREE_ENTRIES = 2048;
const MAX_TREE_DEPTH = 5;
const MAX_CANARY_FILE_BYTES = 64 * 1024;
const MAX_PROCESSES = 256;
const TIMING_SAMPLES = 32;
const CANARY_PATTERN = /WAVE025_CANARY_[A-Za-z0-9._-]{1,96}/g;

const RUNTIME_PATHS = Object.freeze({
  challengeRoot: "/challenge",
  configPath: "/challenge/collector-input.json",
  subjectPath: "/challenge/input.bin",
  outRoot: "/out",
  outputPath: "/out/leak-features.json",
  procRoot: "/proc",
  tmpRoot: "/tmp",
});

class CollectorInputError extends Error {
  constructor(message, code = "INVALID_COLLECTOR_INPUT") {
    super(message);
    this.name = "CollectorInputError";
    this.code = code;
  }
}

function canonicalize(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TypeError("canonical JSON cannot contain non-finite numbers");
    }
    return value;
  }
  if (typeof value === "bigint") {
    return value.toString(10);
  }
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      if (value[key] === undefined) {
        continue;
      }
      result[key] = canonicalize(value[key]);
    }
    return result;
  }
  throw new TypeError(`unsupported canonical JSON type: ${typeof value}`);
}

function canonicalStringify(value) {
  return JSON.stringify(canonicalize(value));
}

function sha256Bytes(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function byteLength(value) {
  return Buffer.byteLength(value, "utf8");
}

function validateCollectorInput(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new CollectorInputError("collector input must be one JSON object");
  }
  const keys = Object.keys(value).sort();
  if (keys.length !== 1 || keys[0] !== "schema") {
    const unknown = keys.filter((key) => key !== "schema");
    throw new CollectorInputError(
      `collector input fields must be exactly [schema]; unknown=${unknown.join(",")}`,
      "UNKNOWN_INPUT_FIELD",
    );
  }
  if (value.schema !== INPUT_SCHEMA) {
    throw new CollectorInputError(
      `collector input schema must be ${INPUT_SCHEMA}`,
      "WRONG_INPUT_SCHEMA",
    );
  }
  return { schema: INPUT_SCHEMA };
}

function readStrictInput(configPath) {
  let raw;
  try {
    raw = fs.readFileSync(configPath);
  } catch (error) {
    throw new CollectorInputError(
      `cannot read fixed collector input: ${normalizeError(error, {})?.code || "UNKNOWN"}`,
      "INPUT_READ_FAILED",
    );
  }
  let parsed;
  try {
    parsed = JSON.parse(raw.toString("utf8"));
  } catch {
    throw new CollectorInputError("collector input is not valid JSON", "INPUT_JSON_INVALID");
  }
  return {
    parsed: validateCollectorInput(parsed),
    byte_length: raw.length,
    sha256: sha256Bytes(raw),
  };
}

function replacePrefix(value, prefix, replacement) {
  if (!prefix || typeof value !== "string") {
    return value;
  }
  return value.split(prefix).join(replacement);
}

function normalizeVisiblePath(value, roots) {
  let normalized = String(value);
  const replacements = [
    [roots.challengeRoot, "$CHALLENGE"],
    [roots.outRoot, "$OUT"],
    [roots.tmpRoot, "$TMP"],
    [roots.cwdRoot, "$CWD"],
    [roots.procRoot, "$PROC"],
  ].sort((left, right) => String(right[0]).length - String(left[0]).length);
  for (const [prefix, replacement] of replacements) {
    normalized = replacePrefix(normalized, prefix, replacement);
  }
  return normalized;
}

function normalizeError(error, roots) {
  if (!error) {
    return null;
  }
  const message = normalizeVisiblePath(error.message || String(error), roots);
  return {
    name: String(error.name || "Error"),
    code: error.code === undefined ? null : String(error.code),
    errno: error.errno === undefined ? null : String(error.errno),
    syscall: error.syscall === undefined ? null : String(error.syscall),
    path: error.path === undefined ? null : normalizeVisiblePath(error.path, roots),
    message,
  };
}

function safeReadlink(target) {
  try {
    return fs.readlinkSync(target);
  } catch {
    return null;
  }
}

function classifyStat(stat) {
  if (stat.isDirectory()) return "directory";
  if (stat.isFile()) return "file";
  if (stat.isSymbolicLink()) return "symlink";
  if (stat.isSocket()) return "socket";
  if (stat.isFIFO()) return "fifo";
  if (stat.isCharacterDevice()) return "character-device";
  if (stat.isBlockDevice()) return "block-device";
  return "other";
}

function statFeature(fullPath, relativePath) {
  const stat = fs.lstatSync(fullPath, { bigint: true });
  const entry = {
    path: relativePath || ".",
    type: classifyStat(stat),
    mode_octal: `0o${(Number(stat.mode) & 0o7777).toString(8).padStart(4, "0")}`,
    uid: stat.uid.toString(10),
    gid: stat.gid.toString(10),
    size_bytes: stat.size.toString(10),
    inode: stat.ino.toString(10),
    device: stat.dev.toString(10),
    nlink: stat.nlink.toString(10),
    mtime_ns: stat.mtimeNs.toString(10),
    ctime_ns: stat.ctimeNs.toString(10),
  };
  if (stat.isSymbolicLink()) {
    entry.symlink_target = safeReadlink(fullPath);
  }
  return { entry, stat };
}

function collectTree(root, options = {}) {
  const maxEntries = options.maxEntries || MAX_TREE_ENTRIES;
  const maxDepth = options.maxDepth || MAX_TREE_DEPTH;
  const entries = [];
  const errors = [];
  let truncated = false;

  function visit(fullPath, relativePath, depth) {
    if (entries.length >= maxEntries) {
      truncated = true;
      return;
    }
    let feature;
    let stat;
    try {
      ({ entry: feature, stat } = statFeature(fullPath, relativePath));
      entries.push(feature);
    } catch (error) {
      errors.push({
        path: relativePath || ".",
        error: normalizeError(error, options.roots || {}),
      });
      return;
    }
    if (!stat.isDirectory() || depth >= maxDepth) {
      if (stat.isDirectory() && depth >= maxDepth) truncated = true;
      return;
    }
    let children;
    try {
      children = fs.readdirSync(fullPath).sort((a, b) => a.localeCompare(b, "en"));
    } catch (error) {
      errors.push({
        path: relativePath || ".",
        error: normalizeError(error, options.roots || {}),
      });
      return;
    }
    for (const child of children) {
      if (entries.length >= maxEntries) {
        truncated = true;
        break;
      }
      visit(
        path.join(fullPath, child),
        relativePath ? `${relativePath}/${child}` : child,
        depth + 1,
      );
    }
  }

  if (!fs.existsSync(root)) {
    return { available: false, entries: [], errors: [], truncated: false };
  }
  visit(root, "", 0);
  return { available: true, entries, errors, truncated };
}

function collectEnvironment(environment) {
  return Object.keys(environment)
    .sort()
    .map((key) => {
      const value = String(environment[key]);
      return {
        key,
        value_byte_length: byteLength(value),
        value_sha256: sha256Bytes(Buffer.from(value, "utf8")),
      };
    });
}

function readProcText(filePath, maxBytes = 64 * 1024) {
  const value = fs.readFileSync(filePath);
  return value.subarray(0, maxBytes);
}

function parseStatus(text) {
  const result = {};
  for (const line of text.split("\n")) {
    const separator = line.indexOf(":");
    if (separator < 0) continue;
    const key = line.slice(0, separator);
    if (["Name", "State", "PPid", "Uid", "Gid", "Threads"].includes(key)) {
      result[key.toLowerCase()] = line.slice(separator + 1).trim();
    }
  }
  return result;
}

function collectProcessView(procRoot) {
  if (!fs.existsSync(procRoot)) {
    return { available: false, processes: [], self: null, truncated: false };
  }
  let names;
  try {
    names = fs.readdirSync(procRoot);
  } catch (error) {
    return {
      available: false,
      processes: [],
      self: null,
      truncated: false,
      error: normalizeError(error, { procRoot }),
    };
  }
  const numeric = names
    .filter((name) => /^[0-9]+$/.test(name))
    .map(Number)
    .sort((a, b) => a - b);
  const selected = numeric.slice(0, MAX_PROCESSES);
  const processes = [];
  for (const pid of selected) {
    const processRoot = path.join(procRoot, String(pid));
    try {
      const cmdlineRaw = readProcText(path.join(processRoot, "cmdline"));
      const cmdline = cmdlineRaw
        .toString("utf8")
        .split("\0")
        .filter((item) => item.length > 0);
      const status = parseStatus(readProcText(path.join(processRoot, "status")).toString("utf8"));
      processes.push({
        pid,
        cmdline,
        cmdline_byte_length: cmdlineRaw.length,
        cmdline_sha256: sha256Bytes(cmdlineRaw),
        status,
        pid_namespace: safeReadlink(path.join(processRoot, "ns", "pid")),
        mount_namespace: safeReadlink(path.join(processRoot, "ns", "mnt")),
      });
    } catch (error) {
      processes.push({ pid, error: normalizeError(error, { procRoot }) });
    }
  }
  const self = {};
  for (const filename of ["cgroup", "mountinfo", "status"] ) {
    try {
      const value = readProcText(path.join(procRoot, "self", filename));
      self[filename] = {
        byte_length: value.length,
        sha256: sha256Bytes(value),
      };
    } catch (error) {
      self[filename] = { error: normalizeError(error, { procRoot }) };
    }
  }
  self.pid_namespace = safeReadlink(path.join(procRoot, "self", "ns", "pid"));
  self.mount_namespace = safeReadlink(path.join(procRoot, "self", "ns", "mnt"));
  return {
    available: true,
    processes,
    self,
    truncated: numeric.length > selected.length,
  };
}

function canaryTokens(text) {
  const matches = String(text).match(CANARY_PATTERN) || [];
  return [...new Set(matches)].sort();
}

function canaryFeature(token, source, location) {
  return {
    source,
    location,
    token_byte_length: byteLength(token),
    token_sha256: sha256Bytes(Buffer.from(token, "utf8")),
  };
}

function collectVisibleCanaries(challengeRoot, environment) {
  const hits = [];
  const seen = new Set();
  function add(token, source, location) {
    const feature = canaryFeature(token, source, location);
    const identity = canonicalStringify(feature);
    if (!seen.has(identity)) {
      seen.add(identity);
      hits.push(feature);
    }
  }

  for (const key of Object.keys(environment).sort()) {
    for (const token of canaryTokens(environment[key])) {
      add(token, "environment-value", key);
    }
    for (const token of canaryTokens(key)) {
      add(token, "environment-key", key);
    }
  }

  function visit(fullPath, relativePath, depth) {
    if (depth > MAX_TREE_DEPTH || hits.length >= MAX_TREE_ENTRIES) return;
    let stat;
    try {
      stat = fs.lstatSync(fullPath);
    } catch {
      return;
    }
    for (const token of canaryTokens(path.basename(fullPath))) {
      add(token, "challenge-entry-name", relativePath || ".");
    }
    if (stat.isSymbolicLink()) {
      const target = safeReadlink(fullPath);
      for (const token of canaryTokens(target || "")) {
        add(token, "challenge-symlink-target", relativePath || ".");
      }
      return;
    }
    if (stat.isFile() && stat.size <= MAX_CANARY_FILE_BYTES) {
      try {
        const content = fs.readFileSync(fullPath).toString("utf8");
        for (const token of canaryTokens(content)) {
          add(token, "challenge-file-content", relativePath || ".");
        }
      } catch {
        // Visibility failures are represented by the directory/error features.
      }
      return;
    }
    if (!stat.isDirectory()) return;
    let children;
    try {
      children = fs.readdirSync(fullPath).sort((a, b) => a.localeCompare(b, "en"));
    } catch {
      return;
    }
    for (const child of children) {
      visit(
        path.join(fullPath, child),
        relativePath ? `${relativePath}/${child}` : child,
        depth + 1,
      );
    }
  }

  if (fs.existsSync(challengeRoot)) visit(challengeRoot, "", 0);
  return hits.sort((left, right) => canonicalStringify(left).localeCompare(canonicalStringify(right), "en"));
}

function measureOperation(name, operation, roots) {
  const start = process.hrtime.bigint();
  try {
    operation();
    return {
      name,
      ok: true,
      elapsed_ns: (process.hrtime.bigint() - start).toString(10),
      error: null,
    };
  } catch (error) {
    return {
      name,
      ok: false,
      elapsed_ns: (process.hrtime.bigint() - start).toString(10),
      error: normalizeError(error, roots),
    };
  }
}

function captureValue(operation, roots) {
  try {
    return { ok: true, value: operation(), error: null };
  } catch (error) {
    return { ok: false, value: null, error: normalizeError(error, roots) };
  }
}

function collectTiming(subjectPath, roots) {
  const wallStart = Date.now();
  const monotonicStart = process.hrtime.bigint();
  const immediateDeltas = [];
  let previous = process.hrtime.bigint();
  for (let index = 0; index < TIMING_SAMPLES; index += 1) {
    const current = process.hrtime.bigint();
    immediateDeltas.push((current - previous).toString(10));
    previous = current;
  }
  const statSamples = [];
  for (let index = 0; index < TIMING_SAMPLES; index += 1) {
    const start = process.hrtime.bigint();
    fs.statSync(subjectPath);
    statSamples.push((process.hrtime.bigint() - start).toString(10));
  }
  return {
    wall_clock_start_ms: wallStart,
    wall_clock_end_ms: Date.now(),
    monotonic_start_ns: monotonicStart.toString(10),
    monotonic_end_ns: process.hrtime.bigint().toString(10),
    process_uptime_seconds: captureValue(() => process.uptime(), roots),
    os_uptime_seconds: captureValue(() => os.uptime(), roots),
    immediate_delta_ns: immediateDeltas,
    input_stat_elapsed_ns: statSamples,
    error_shape_probes: [
      measureOperation(
        "read-fixed-missing-file",
        () => fs.readFileSync(path.join(roots.challengeRoot, "__collector_missing_probe__")),
        roots,
      ),
      measureOperation(
        "stat-fixed-missing-proc",
        () => fs.statSync(path.join(roots.procRoot, "0", "__collector_missing_probe__")),
        roots,
      ),
      measureOperation(
        "read-challenge-directory-as-file",
        () => fs.readFileSync(roots.challengeRoot),
        roots,
      ),
    ],
  };
}

function collectIdentity() {
  let userInfo;
  try {
    const value = os.userInfo();
    userInfo = {
      username: value.username,
      uid: value.uid,
      gid: value.gid,
      homedir: value.homedir,
      shell: value.shell,
    };
  } catch (error) {
    userInfo = { error: normalizeError(error, {}) };
  }
  return {
    pid: process.pid,
    ppid: process.ppid,
    uid: typeof process.getuid === "function" ? process.getuid() : null,
    euid: typeof process.geteuid === "function" ? process.geteuid() : null,
    gid: typeof process.getgid === "function" ? process.getgid() : null,
    egid: typeof process.getegid === "function" ? process.getegid() : null,
    groups: typeof process.getgroups === "function" ? process.getgroups().slice().sort((a, b) => a - b) : [],
    user_info: userInfo,
  };
}

function collectFeatures(options = {}) {
  const runtime = {
    ...RUNTIME_PATHS,
    ...options,
  };
  runtime.cwdRoot = options.cwdRoot || process.cwd();
  const input = readStrictInput(runtime.configPath);
  const subject = fs.readFileSync(runtime.subjectPath);
  const collectionStart = {
    wall_clock_ms: Date.now(),
    monotonic_ns: process.hrtime.bigint().toString(10),
  };
  const directoryRoots = [
    ["challenge", runtime.challengeRoot],
    ["cwd", runtime.cwdRoot],
    ["out", runtime.outRoot],
    ["tmp", runtime.tmpRoot],
    ["self-fd", path.join(runtime.procRoot, "self", "fd")],
  ];
  const directoryTrees = {};
  for (const [label, root] of directoryRoots) {
    directoryTrees[label] = collectTree(root, { roots: runtime });
  }
  const features = {
    schema: OUTPUT_SCHEMA,
    collector_version: COLLECTOR_VERSION,
    contract: {
      mode: "LEAK_ONLY_FEATURE_COLLECTION",
      lawful_truth_api_calls: 0,
      network_calls: 0,
      accepted_input_fields: ["schema"],
      prohibited_control_fields: ["expected", "order", "role", "seed"],
      does_not_score_leakage: true,
      does_not_rank_treatments: true,
    },
    input_contract: input,
    subject_input: {
      path: "$CHALLENGE/input.bin",
      byte_length: subject.length,
      sha256: sha256Bytes(subject),
    },
    argv: process.argv.slice(),
    environment: collectEnvironment(process.env),
    cwd: process.cwd(),
    hostname: {
      os_hostname: captureValue(() => os.hostname(), runtime),
      etc_hostname: (() => {
        try {
          return fs.readFileSync("/etc/hostname", "utf8").trim();
        } catch (error) {
          return { error: normalizeError(error, runtime) };
        }
      })(),
    },
    identity: collectIdentity(),
    directory_trees: directoryTrees,
    process_view: collectProcessView(runtime.procRoot),
    visible_canaries: collectVisibleCanaries(runtime.challengeRoot, process.env),
    timing: collectTiming(runtime.subjectPath, runtime),
    collection_window: {
      start: collectionStart,
      end: {
        wall_clock_ms: Date.now(),
        monotonic_ns: process.hrtime.bigint().toString(10),
      },
    },
  };
  return canonicalize(features);
}

function writeCanonicalExclusive(outputPath, value) {
  const rendered = `${canonicalStringify(value)}\n`;
  fs.writeFileSync(outputPath, rendered, { encoding: "utf8", flag: "wx", mode: 0o600 });
  return rendered;
}

function failureDocument(error) {
  return canonicalize({
    schema: FAILURE_SCHEMA,
    collector_version: COLLECTOR_VERSION,
    status: "REJECTED",
    error: {
      name: String(error.name || "Error"),
      code: error.code === undefined ? "COLLECTOR_FAILURE" : String(error.code),
      message: String(error.message || error),
    },
  });
}

function main() {
  if (process.argv.length !== 2) {
    const failure = failureDocument(
      new CollectorInputError("collector accepts no command-line fields", "UNEXPECTED_ARGV"),
    );
    process.stdout.write(`${canonicalStringify(failure)}\n`);
    return 64;
  }
  try {
    const features = collectFeatures();
    const rendered = writeCanonicalExclusive(RUNTIME_PATHS.outputPath, features);
    process.stdout.write(rendered);
    return 0;
  } catch (error) {
    const failure = failureDocument(error);
    process.stdout.write(`${canonicalStringify(failure)}\n`);
    return error instanceof CollectorInputError ? 64 : 70;
  }
}

if (require.main === module) {
  process.exitCode = main();
}

module.exports = {
  CollectorInputError,
  FAILURE_SCHEMA,
  INPUT_SCHEMA,
  OUTPUT_SCHEMA,
  RUNTIME_PATHS,
  canonicalStringify,
  canonicalize,
  collectFeatures,
  collectProcessView,
  collectTree,
  collectVisibleCanaries,
  failureDocument,
  normalizeError,
  readStrictInput,
  sha256Bytes,
  validateCollectorInput,
  writeCanonicalExclusive,
};
