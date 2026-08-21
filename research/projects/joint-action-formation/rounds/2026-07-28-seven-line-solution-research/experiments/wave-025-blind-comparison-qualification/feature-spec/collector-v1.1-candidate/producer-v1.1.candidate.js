#!/usr/bin/env node
"use strict";

/*
 * Candidate producer adapter only.  It deliberately leaves the public receipt
 * at WAVE025_LEAK_ONLY_FEATURES_V1 so existing F evidence is not reinterpreted.
 * The adapter makes a stricter, fail-closed subset of that language and is
 * identified by its source hash in the separate V1.1 admission policy.
 */

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const PACKAGE_DIR = __dirname;
const PACKAGE_MANIFEST_PATH = path.join(PACKAGE_DIR, "PACKAGE-MANIFEST.candidate.json");
const BASE_SOURCE_PATH = path.resolve(PACKAGE_DIR, "../../attackers/leak-only-collector/collector.js");
let base = null;

const ADAPTER_VERSION = "1.1.0-candidate";
const MAX_ENVIRONMENT_ROWS = 4096;
const MAX_TREE_ERRORS = 8192;
const MAX_VISIBLE_CANARIES = 65536;
const MAX_CANARY_NODES = 2048;
const MAX_CANARY_FILE_BYTES = 64 * 1024;
const MAX_SUBJECT_BYTES = 1024 * 1024 * 1024;
const MAX_STRING_CODE_POINTS = 1024 * 1024;
const MAX_TREE_DEPTH = 5;
const MAX_PROC_DIRECTORY_ENTRIES = 4096;
const MAX_PROC_DIRECTORY_NAME_BYTES = 1024 * 1024;
const CANARY_PATTERN = /WAVE025_CANARY_[A-Za-z0-9._-]{1,96}/g;
const OUTPUT_SCHEMA = "WAVE025_LEAK_ONLY_FEATURES_V1";

class CandidateAdmissionError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "CandidateAdmissionError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new CandidateAdmissionError(code, message);
}

function canonicalize(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) fail("CANONICAL_NUMBER", "non-finite number");
    return value;
  }
  if (Array.isArray(value)) return value.map(canonicalize);
  if (typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) result[key] = canonicalize(value[key]);
    return result;
  }
  fail("CANONICAL_TYPE", typeof value);
}

function canonicalStringify(value) {
  return JSON.stringify(canonicalize(value));
}

function verifyPackageAtStartup(expectedManifestSha256) {
  if (!/^[0-9a-f]{64}$/.test(String(expectedManifestSha256 || ""))) {
    fail("PACKAGE_SEAL_REQUIRED", "exact controller-supplied manifest SHA-256 is required");
  }
  let raw;
  try {
    raw = fs.readFileSync(PACKAGE_MANIFEST_PATH);
  } catch (error) {
    fail("PACKAGE_MANIFEST_MISSING", error.code || error.name);
  }
  if (sha256(raw) !== expectedManifestSha256) fail("PACKAGE_MANIFEST_SEAL_MISMATCH", sha256(raw));
  let manifest;
  try {
    manifest = JSON.parse(raw.toString("utf8"));
  } catch {
    fail("PACKAGE_MANIFEST_JSON", "manifest is not strict JSON");
  }
  if (!raw.equals(Buffer.from(`${canonicalStringify(manifest)}\n`, "utf8"))) {
    fail("PACKAGE_MANIFEST_CANONICAL", "manifest bytes are not canonical");
  }
  if (manifest.schema !== "WAVE025_COLLECTOR_ADMISSION_PACKAGE_MANIFEST_V1_1_CANDIDATE") {
    fail("PACKAGE_MANIFEST_SCHEMA", String(manifest.schema));
  }
  const requiredFiles = [
    "ADMISSION-POLICY-V1.1.candidate.json", "COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json",
    "EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json", "admit_receipt_v1_1.py",
    "producer-v1.1.candidate.js", "raw-canonical-check.candidate.js",
  ].sort();
  const requiredHistorical = [
    "../../attackers/leak-only-collector/collector.js", "../COLLECTOR-RECEIPT-V1.candidate.schema.json",
  ].sort();
  if (!Array.isArray(manifest.files) || !Array.isArray(manifest.historical_inputs)) fail("PACKAGE_MANIFEST_FIELDS", "file arrays");
  if (manifest.files.map((row) => row.path).sort().join("\n") !== requiredFiles.join("\n")) fail("PACKAGE_MANIFEST_FILE_SET", "runtime file set differs");
  if (manifest.historical_inputs.map((row) => row.path).sort().join("\n") !== requiredHistorical.join("\n")) fail("PACKAGE_MANIFEST_HISTORICAL_SET", "historical input set differs");
  for (const group of ["files", "historical_inputs"]) {
    if (!Array.isArray(manifest[group])) fail("PACKAGE_MANIFEST_FIELDS", group);
    for (const row of manifest[group]) {
      if (!row || Object.keys(row).sort().join(",") !== "byte_length,path,sha256") {
        fail("PACKAGE_MANIFEST_ENTRY", group);
      }
      const target = path.resolve(PACKAGE_DIR, row.path);
      let value;
      try {
        value = fs.readFileSync(target);
      } catch (error) {
        fail("PACKAGE_FILE_MISSING", `${row.path}:${error.code || error.name}`);
      }
      if (value.length !== row.byte_length || sha256(value) !== row.sha256) {
        fail("PACKAGE_FILE_MISMATCH", row.path);
      }
    }
  }
  if (!base) base = require(BASE_SOURCE_PATH);
  return manifest;
}

function utf8Compare(left, right) {
  return Buffer.compare(Buffer.from(String(left), "utf8"), Buffer.from(String(right), "utf8"));
}

function canonicalByteCompare(left, right) {
  return utf8Compare(canonicalStringify(left), canonicalStringify(right));
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function canaryTokens(value) {
  return [...new Set(String(value).match(CANARY_PATTERN) || [])].sort(utf8Compare);
}

function canaryRow(token, source, location) {
  const raw = Buffer.from(token, "utf8");
  return {
    source,
    location,
    token_byte_length: raw.length,
    token_sha256: sha256(raw),
  };
}

function scanVisibleCanariesComplete(challengeRoot, environment) {
  const rows = [];
  const seen = new Set();
  let nodes = 0;

  function add(token, source, location) {
    const row = canaryRow(token, source, location);
    const identity = canonicalStringify(row);
    if (seen.has(identity)) return;
    if (rows.length >= MAX_VISIBLE_CANARIES) {
      fail("VISIBLE_CANARY_CAP", `more than ${MAX_VISIBLE_CANARIES} visible canaries`);
    }
    seen.add(identity);
    rows.push(row);
  }

  const environmentKeys = Object.keys(environment).sort(utf8Compare);
  for (const key of environmentKeys) {
    for (const token of canaryTokens(environment[key])) add(token, "environment-value", key);
    for (const token of canaryTokens(key)) add(token, "environment-key", key);
  }

  function visit(fullPath, relativePath, depth) {
    if (nodes >= MAX_CANARY_NODES) {
      fail("CANARY_SCAN_NODE_CAP", `challenge scan exceeds ${MAX_CANARY_NODES} nodes`);
    }
    nodes += 1;
    let stat;
    try {
      stat = fs.lstatSync(fullPath);
    } catch (error) {
      fail("CANARY_SCAN_LSTAT", `${relativePath || "."}: ${error.code || error.name}`);
    }
    for (const token of canaryTokens(path.basename(fullPath))) {
      add(token, "challenge-entry-name", relativePath || ".");
    }
    if (stat.isSymbolicLink()) {
      let target;
      try {
        target = fs.readlinkSync(fullPath);
      } catch (error) {
        fail("CANARY_SCAN_READLINK", `${relativePath || "."}: ${error.code || error.name}`);
      }
      for (const token of canaryTokens(target)) {
        add(token, "challenge-symlink-target", relativePath || ".");
      }
      return;
    }
    if (stat.isFile()) {
      // Files above this bound are explicitly outside the declared scan domain.
      if (stat.size > MAX_CANARY_FILE_BYTES) return;
      let content;
      try {
        content = fs.readFileSync(fullPath).toString("utf8");
      } catch (error) {
        fail("CANARY_SCAN_READ", `${relativePath || "."}: ${error.code || error.name}`);
      }
      for (const token of canaryTokens(content)) {
        add(token, "challenge-file-content", relativePath || ".");
      }
      return;
    }
    if (!stat.isDirectory()) return;
    let children;
    try {
      children = fs.readdirSync(fullPath).sort(utf8Compare);
    } catch (error) {
      fail("CANARY_SCAN_READDIR", `${relativePath || "."}: ${error.code || error.name}`);
    }
    if (depth >= MAX_TREE_DEPTH && children.length > 0) {
      fail("CANARY_SCAN_DEPTH_CAP", `${relativePath || "."} has children beyond depth ${MAX_TREE_DEPTH}`);
    }
    for (const child of children) {
      visit(
        path.join(fullPath, child),
        relativePath ? `${relativePath}/${child}` : child,
        depth + 1,
      );
    }
  }

  if (!fs.existsSync(challengeRoot)) fail("CANARY_ROOT_MISSING", "challenge root must exist");
  visit(challengeRoot, "", 0);
  return rows.sort(canonicalByteCompare);
}

function assertCanonicalProcProvider(procRoot) {
  if (!fs.existsSync(procRoot)) return;
  let directory;
  let totalEntries = 0;
  let totalNameBytes = 0;
  const seen = new Set();
  const numericNames = [];
  try {
    directory = fs.opendirSync(procRoot);
    let entry;
    while ((entry = directory.readSync()) !== null) {
      totalEntries += 1;
      totalNameBytes += Buffer.byteLength(entry.name, "utf8");
      if (totalEntries > MAX_PROC_DIRECTORY_ENTRIES) {
        fail("PROC_DIRECTORY_ENTRY_CAP", `more than ${MAX_PROC_DIRECTORY_ENTRIES} total proc entries`);
      }
      if (totalNameBytes > MAX_PROC_DIRECTORY_NAME_BYTES) {
        fail("PROC_DIRECTORY_NAME_BYTES_CAP", `more than ${MAX_PROC_DIRECTORY_NAME_BYTES} proc name bytes`);
      }
      if (!/^[0-9]+$/.test(entry.name)) continue;
      const numeric = Number(entry.name);
      if (!Number.isSafeInteger(numeric) || numeric < 0 || String(numeric) !== entry.name) {
        fail("PROC_PID_GRAMMAR", `non-canonical proc PID name: ${entry.name}`);
      }
      if (seen.has(numeric)) fail("PROC_PID_DUPLICATE", `duplicate proc PID: ${numeric}`);
      seen.add(numeric);
      numericNames.push(entry.name);
      if (seen.size > 256) fail("PROCESS_TRUNCATION", "more than 256 numeric proc entries");
    }
  } catch (error) {
    if (error instanceof CandidateAdmissionError) throw error;
    fail("PROC_PROVIDER_READ", error.code || error.name);
  } finally {
    if (directory) try { directory.closeSync(); } catch {}
  }
  return numericNames.sort((left, right) => Number(left) - Number(right));
}

function assertStatusGrammar(status, pointer) {
  const decimal = /^(0|[1-9][0-9]*)$/;
  const vector = /^(0|[1-9][0-9]*)\t(0|[1-9][0-9]*)\t(0|[1-9][0-9]*)\t(0|[1-9][0-9]*)$/;
  for (const field of ["ppid", "threads"]) {
    if (status[field] !== undefined && !decimal.test(status[field])) {
      fail("STATUS_GRAMMAR", `${pointer}.${field}`);
    }
  }
  for (const field of ["uid", "gid"]) {
    if (status[field] !== undefined && !vector.test(status[field])) {
      fail("STATUS_GRAMMAR", `${pointer}.${field}`);
    }
  }
}

function assertNoOversizedString(value, pointer = "$") {
  if (typeof value === "string") {
    if ([...value].length > MAX_STRING_CODE_POINTS) {
      fail("STRING_CODEPOINT_CAP", pointer);
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoOversizedString(item, `${pointer}[${index}]`));
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      assertNoOversizedString(child, `${pointer}.${key}`);
    }
  }
}

function assertMonotonicNesting(receipt) {
  const collectionStart = BigInt(receipt.collection_window.start.monotonic_ns);
  const timingStart = BigInt(receipt.timing.monotonic_start_ns);
  const timingEnd = BigInt(receipt.timing.monotonic_end_ns);
  const collectionEnd = BigInt(receipt.collection_window.end.monotonic_ns);
  if (!(collectionStart <= timingStart && timingStart <= timingEnd && timingEnd <= collectionEnd)) {
    fail("MONOTONIC_NESTING", "collection/timing monotonic intervals are not nested");
  }
  const samples = [...receipt.timing.immediate_delta_ns, ...receipt.timing.input_stat_elapsed_ns]
    .reduce((sum, item) => sum + BigInt(item), 0n);
  if (samples > timingEnd - timingStart) {
    fail("TIMING_SAMPLE_SUM", "timing sample sum exceeds timing interval");
  }
}

function normalizeAndValidateReceipt(receipt, completeCanaries, options = {}) {
  if (receipt.schema !== OUTPUT_SCHEMA || receipt.collector_version !== "1.0.0") {
    fail("BASE_RECEIPT_VERSION", "adapter only accepts the frozen V1 base receipt");
  }
  if (receipt.environment.length > MAX_ENVIRONMENT_ROWS) fail("ENVIRONMENT_CAP", "too many rows");
  const envKeys = new Set();
  for (const row of receipt.environment) {
    if (envKeys.has(row.key)) fail("ENVIRONMENT_IDENTITY", row.key);
    envKeys.add(row.key);
  }
  receipt.environment.sort((a, b) => utf8Compare(a.key, b.key));

  for (const [label, tree] of Object.entries(receipt.directory_trees)) {
    if (tree.truncated) fail("TREE_TRUNCATION", label);
    if (tree.errors.length > MAX_TREE_ERRORS) fail("TREE_ERROR_CAP", label);
    const entryPaths = new Set();
    for (const row of tree.entries) {
      if (entryPaths.has(row.path)) fail("TREE_ENTRY_IDENTITY", `${label}:${row.path}`);
      entryPaths.add(row.path);
    }
    const errorPaths = new Set();
    for (const row of tree.errors) {
      if (errorPaths.has(row.path)) fail("TREE_ERROR_IDENTITY", `${label}:${row.path}`);
      errorPaths.add(row.path);
    }
    tree.entries.sort((a, b) => utf8Compare(a.path, b.path));
    tree.errors.sort((a, b) => utf8Compare(a.path, b.path));
  }

  if (receipt.process_view.truncated) fail("PROCESS_TRUNCATION", "receipt truncated process view");
  const pids = new Set();
  for (const row of receipt.process_view.processes) {
    if (pids.has(row.pid)) fail("PROCESS_IDENTITY", String(row.pid));
    pids.add(row.pid);
    if (!row.error) assertStatusGrammar(row.status, `process[${row.pid}].status`);
  }
  receipt.process_view.processes.sort((a, b) => a.pid - b.pid);

  receipt.visible_canaries = completeCanaries;
  assertMonotonicNesting(receipt);
  assertNoOversizedString(receipt);
  if (options.gMode) {
    if (!receipt.hostname.os_hostname.ok || receipt.hostname.etc_hostname.error) fail("G_UNVERIFIED_ERROR_BRANCH", "hostname");
    if (receipt.identity.user_info.error) fail("G_UNVERIFIED_ERROR_BRANCH", "identity");
    for (const [label, tree] of Object.entries(receipt.directory_trees)) {
      if (!tree.available || tree.errors.length) fail("G_UNVERIFIED_ERROR_BRANCH", `tree:${label}`);
    }
    if (!receipt.process_view.available) fail("G_UNVERIFIED_ERROR_BRANCH", "process unavailable");
    if (receipt.process_view.processes.some((row) => row.error)) fail("G_UNVERIFIED_ERROR_BRANCH", "process row");
    if (!receipt.process_view.processes.some((row) => row.pid === receipt.identity.pid)) fail("G_PROCESS_SELF_PID_MISSING", String(receipt.identity.pid));
    for (const name of ["cgroup", "mountinfo", "status"]) {
      if (receipt.process_view.self[name].error) fail("G_UNVERIFIED_ERROR_BRANCH", `process self:${name}`);
    }
    if (!receipt.timing.process_uptime_seconds.ok || !receipt.timing.os_uptime_seconds.ok) {
      fail("G_UNVERIFIED_ERROR_BRANCH", "uptime");
    }
  }
  return canonicalize(receipt);
}

function preflightTreeDomains(runtime) {
  const roots = [
    ["challenge", runtime.challengeRoot], ["cwd", runtime.cwdRoot], ["out", runtime.outRoot],
    ["tmp", runtime.tmpRoot], ["self-fd", path.join(runtime.procRoot, "self", "fd")],
  ];
  const observations = [];
  for (const [label, root] of roots) {
    if (!fs.existsSync(root)) fail("G_PREFLIGHT_ROOT_MISSING", label);
    let count = 0;
    function visit(fullPath, relative, depth) {
      if (count >= 2048) fail("G_PREFLIGHT_TREE_CAP", label);
      count += 1;
      let value;
      try {
        value = fs.lstatSync(fullPath, { bigint: true });
      } catch (error) {
        fail("G_PREFLIGHT_TREE_ERROR", `${label}:${relative || "."}:${error.code || error.name}`);
      }
      const row = {
        label, path: relative || ".", mode: value.mode.toString(), size: value.size.toString(),
        inode: value.ino.toString(), device: value.dev.toString(), mtime: value.mtimeNs.toString(),
        ctime: value.ctimeNs.toString(), type: value.isDirectory() ? "directory" : value.isFile() ? "file" : value.isSymbolicLink() ? "symlink" : "other",
      };
      if (label === "challenge" && value.isFile()) {
        if (value.size > BigInt(MAX_CANARY_FILE_BYTES)) fail("G_CANARY_FILE_OVERSIZE", row.path);
        const raw = fs.readFileSync(fullPath);
        if (raw.length > MAX_CANARY_FILE_BYTES) fail("G_CANARY_FILE_TOCTOU", row.path);
        row.sha256 = sha256(raw);
      }
      if (value.isSymbolicLink()) row.target = fs.readlinkSync(fullPath);
      observations.push(row);
      if (!value.isDirectory()) return;
      if (depth >= MAX_TREE_DEPTH) fail("G_PREFLIGHT_TREE_DEPTH", `${label}:${row.path}`);
      let directory;
      try {
        directory = fs.opendirSync(fullPath);
        const names = [];
        let entry;
        while ((entry = directory.readSync()) !== null) {
          if (names.length >= 2048) fail("G_PREFLIGHT_DIRECTORY_CAP", `${label}:${row.path}`);
          names.push(entry.name);
        }
        directory.closeSync();
        directory = null;
        names.sort(utf8Compare);
        for (const name of names) visit(path.join(fullPath, name), relative ? `${relative}/${name}` : name, depth + 1);
      } catch (error) {
        if (directory) try { directory.closeSync(); } catch {}
        if (error instanceof CandidateAdmissionError) throw error;
        fail("G_PREFLIGHT_READDIR", `${label}:${row.path}:${error.code || error.name}`);
      }
    }
    visit(root, "", 0);
  }
  observations.sort(canonicalByteCompare);
  return sha256(Buffer.from(canonicalStringify(observations), "utf8"));
}

function collectCandidate(options = {}) {
  verifyPackageAtStartup(options.packageManifestSha256);
  const runtime = { ...base.RUNTIME_PATHS, ...options };
  runtime.cwdRoot = options.cwdRoot || process.cwd();
  const environment = options.environment || process.env;
  if (Object.keys(environment).length > MAX_ENVIRONMENT_ROWS) {
    fail("ENVIRONMENT_CAP", `more than ${MAX_ENVIRONMENT_ROWS} environment rows`);
  }
  const subject = fs.statSync(runtime.subjectPath);
  if (subject.size > MAX_SUBJECT_BYTES) fail("SUBJECT_CAP", `subject exceeds ${MAX_SUBJECT_BYTES} bytes`);
  const boundedProcNames = assertCanonicalProcProvider(runtime.procRoot) || [];
  for (const [key, value] of Object.entries(environment)) {
    assertNoOversizedString(String(key), `environment.key:${key}`);
    assertNoOversizedString(String(value), `environment.value:${key}`);
  }
  assertNoOversizedString(process.argv, "argv");
  assertNoOversizedString(process.cwd(), "cwd");
  if (options.gMode && fs.statSync("/etc/hostname").size > MAX_STRING_CODE_POINTS) {
    fail("G_HOSTNAME_FILE_CAP", "/etc/hostname");
  }

  // The base collector currently reads process.env.  A different test environment
  // is rejected rather than silently claiming it was collected.
  if (environment !== process.env) fail("ENVIRONMENT_INJECTION_UNSUPPORTED", "use the launched process environment");
  const beforeFingerprint = options.gMode ? preflightTreeDomains(runtime) : null;
  const beforeCanaries = options.gMode ? scanVisibleCanariesComplete(runtime.challengeRoot, environment) : null;
  let receipt;
  if (options.gMode) {
    const originalReaddirSync = fs.readdirSync;
    const procRootResolved = path.resolve(runtime.procRoot);
    fs.readdirSync = function boundedProcReaddir(target, ...args) {
      if (path.resolve(String(target)) === procRootResolved) return boundedProcNames.slice();
      return originalReaddirSync.call(fs, target, ...args);
    };
    try {
      receipt = base.collectFeatures(options);
    } finally {
      fs.readdirSync = originalReaddirSync;
    }
  } else {
    receipt = base.collectFeatures(options);
  }
  const canaries = scanVisibleCanariesComplete(runtime.challengeRoot, environment);
  if (options.gMode && canonicalStringify(canaries) !== canonicalStringify(beforeCanaries)) {
    fail("G_CANARY_DOMAIN_CHANGED", "visible canary domain changed during collection");
  }
  const normalized = normalizeAndValidateReceipt(receipt, canaries, options);
  if (options.gMode && preflightTreeDomains(runtime) !== beforeFingerprint) {
    fail("G_PREFLIGHT_DOMAIN_CHANGED", "tree domains changed during collection");
  }
  return normalized;
}

function writeExclusive(outputPath, value) {
  const raw = `${canonicalStringify(value)}\n`;
  fs.writeFileSync(outputPath, raw, { encoding: "utf8", flag: "wx", mode: 0o600 });
  return raw;
}

function main() {
  const expectedManifest = process.env.WAVE025_PACKAGE_MANIFEST_SHA256;
  if (process.argv.length !== 2) {
    try {
      verifyPackageAtStartup(expectedManifest);
    } catch (error) {
      process.stdout.write(`${canonicalStringify({schema:"WAVE025_COLLECTOR_V1_1_CANDIDATE_FAILURE",adapter_version:ADAPTER_VERSION,status:"REJECTED",error:{code:String(error.code || "PACKAGE_FAILURE")}})}\n`);
      return 70;
    }
    process.stdout.write(`${canonicalStringify({schema:"WAVE025_COLLECTOR_V1_1_CANDIDATE_FAILURE",adapter_version:ADAPTER_VERSION,status:"REJECTED",error:{code:"UNEXPECTED_ARGV"}})}\n`);
    return 64;
  }
  try {
    const receipt = collectCandidate({packageManifestSha256: expectedManifest, gMode: process.env.WAVE025_G_MODE === "1"});
    process.stdout.write(writeExclusive("/out/leak-features.json", receipt));
    return 0;
  } catch (error) {
    process.stdout.write(`${canonicalStringify({schema:"WAVE025_COLLECTOR_V1_1_CANDIDATE_FAILURE",adapter_version:ADAPTER_VERSION,status:"REJECTED",error:{code:String(error.code || "COLLECTOR_FAILURE"),message:String(error.message || error)}})}\n`);
    return 70;
  }
}

if (require.main === module) process.exitCode = main();

module.exports = {
  ADAPTER_VERSION,
  CandidateAdmissionError,
  assertCanonicalProcProvider,
  collectCandidate,
  normalizeAndValidateReceipt,
  preflightTreeDomains,
  scanVisibleCanariesComplete,
  utf8Compare,
  verifyPackageAtStartup,
};
