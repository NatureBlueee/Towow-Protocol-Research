"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const collector = require("../collector.js");


function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "wave025-leak-collector-"));
  const challengeRoot = path.join(root, "challenge");
  const outRoot = path.join(root, "out");
  const tmpRoot = path.join(root, "tmp");
  const cwdRoot = path.join(root, "app");
  const procRoot = path.join(root, "proc");
  for (const directory of [challengeRoot, outRoot, tmpRoot, cwdRoot, procRoot]) {
    fs.mkdirSync(directory, { recursive: true });
  }
  const configPath = path.join(challengeRoot, "collector-input.json");
  const subjectPath = path.join(challengeRoot, "input.bin");
  const outputPath = path.join(outRoot, "leak-features.json");
  fs.writeFileSync(
    configPath,
    `${JSON.stringify({ schema: collector.INPUT_SCHEMA })}\n`,
  );
  fs.writeFileSync(subjectPath, Buffer.from([0, 1, 2, 3, 255]));
  fs.writeFileSync(path.join(cwdRoot, "collector-visible-file"), "visible");

  const procPid = path.join(procRoot, "7");
  fs.mkdirSync(path.join(procPid, "ns"), { recursive: true });
  fs.mkdirSync(path.join(procPid, "fd"), { recursive: true });
  fs.writeFileSync(path.join(procPid, "cmdline"), "node\0/app/collector.js\0");
  fs.writeFileSync(
    path.join(procPid, "status"),
    "Name:\tnode\nState:\tR (running)\nPPid:\t0\nUid:\t1000\t1000\t1000\t1000\nGid:\t1000\t1000\t1000\t1000\nThreads:\t1\n",
  );
  fs.writeFileSync(path.join(procPid, "cgroup"), "0::/collector\n");
  fs.writeFileSync(path.join(procPid, "mountinfo"), "fake mountinfo\n");
  fs.symlinkSync("pid:[4026532999]", path.join(procPid, "ns", "pid"));
  fs.symlinkSync("mnt:[4026533000]", path.join(procPid, "ns", "mnt"));
  fs.symlinkSync("7", path.join(procRoot, "self"));

  return {
    root,
    challengeRoot,
    configPath,
    subjectPath,
    outRoot,
    outputPath,
    tmpRoot,
    cwdRoot,
    procRoot,
  };
}


test("canonical JSON recursively sorts object keys and preserves array order", () => {
  const rendered = collector.canonicalStringify({ z: 1, a: { y: 2, b: 3 }, q: [2, 1] });
  assert.equal(rendered, '{"a":{"b":3,"y":2},"q":[2,1],"z":1}');
});


test("strict input accepts only the fixed schema", () => {
  assert.deepEqual(
    collector.validateCollectorInput({ schema: collector.INPUT_SCHEMA }),
    { schema: collector.INPUT_SCHEMA },
  );
});


for (const forbidden of ["role", "expected", "order", "seed", "other"]) {
  test(`strict input rejects unknown field ${forbidden}`, () => {
    assert.throws(
      () => collector.validateCollectorInput({
        schema: collector.INPUT_SCHEMA,
        [forbidden]: "hidden-control",
      }),
      (error) => error instanceof collector.CollectorInputError
        && error.code === "UNKNOWN_INPUT_FIELD",
    );
  });
}


test("strict input rejects wrong schema and non-object input", () => {
  assert.throws(
    () => collector.validateCollectorInput({ schema: "WRONG" }),
    (error) => error.code === "WRONG_INPUT_SCHEMA",
  );
  assert.throws(
    () => collector.validateCollectorInput([collector.INPUT_SCHEMA]),
    collector.CollectorInputError,
  );
});


test("collector emits all required feature families without parsing subject bytes", (t) => {
  const fixture = makeFixture();
  t.after(() => fs.rmSync(fixture.root, { recursive: true, force: true }));
  const previousCanary = process.env.COLLECTOR_TEST_CANARY;
  process.env.COLLECTOR_TEST_CANARY = "WAVE025_CANARY_ENV_TEST";
  t.after(() => {
    if (previousCanary === undefined) delete process.env.COLLECTOR_TEST_CANARY;
    else process.env.COLLECTOR_TEST_CANARY = previousCanary;
  });
  fs.writeFileSync(
    path.join(fixture.challengeRoot, "WAVE025_CANARY_FILENAME_TEST.txt"),
    "payload WAVE025_CANARY_CONTENT_TEST",
  );
  fs.symlinkSync(
    "WAVE025_CANARY_SYMLINK_TEST",
    path.join(fixture.challengeRoot, "canary-link"),
  );

  const result = collector.collectFeatures(fixture);

  assert.equal(result.schema, collector.OUTPUT_SCHEMA);
  assert.equal(result.contract.lawful_truth_api_calls, 0);
  assert.equal(result.contract.network_calls, 0);
  assert.equal(result.subject_input.byte_length, 5);
  assert.equal(
    result.subject_input.sha256,
    collector.sha256Bytes(Buffer.from([0, 1, 2, 3, 255])),
  );
  assert.ok(Array.isArray(result.argv));
  assert.ok(Array.isArray(result.environment));
  assert.equal(typeof result.cwd, "string");
  assert.equal(typeof result.hostname.os_hostname.ok, "boolean");
  if (result.hostname.os_hostname.ok) {
    assert.equal(typeof result.hostname.os_hostname.value, "string");
  }
  assert.equal(typeof result.identity.uid === "number" || result.identity.uid === null, true);
  assert.equal(result.directory_trees.challenge.available, true);
  assert.equal(result.directory_trees.cwd.available, true);
  assert.equal(result.process_view.available, true);
  assert.equal(result.process_view.processes[0].pid, 7);
  assert.equal(result.process_view.processes[0].cmdline[1], "/app/collector.js");
  assert.equal(result.timing.immediate_delta_ns.length, 32);
  assert.equal(result.timing.input_stat_elapsed_ns.length, 32);
  assert.equal(result.timing.error_shape_probes.length, 3);
  assert.equal(result.timing.error_shape_probes[0].ok, false);
  assert.equal(result.timing.error_shape_probes[0].error.code, "ENOENT");

  const canaryHashes = new Set(result.visible_canaries.map((item) => item.token_sha256));
  for (const token of [
    "WAVE025_CANARY_ENV_TEST",
    "WAVE025_CANARY_FILENAME_TEST.txt",
    "WAVE025_CANARY_CONTENT_TEST",
    "WAVE025_CANARY_SYMLINK_TEST",
  ]) {
    assert.ok(canaryHashes.has(collector.sha256Bytes(Buffer.from(token))));
  }
  assert.equal(
    result.visible_canaries.some((item) => Object.hasOwn(item, "token")),
    false,
  );
});


test("tree collector records metadata but does not follow symlinks", (t) => {
  const fixture = makeFixture();
  t.after(() => fs.rmSync(fixture.root, { recursive: true, force: true }));
  const outside = path.join(fixture.root, "outside-secret");
  fs.writeFileSync(outside, "secret");
  fs.symlinkSync(outside, path.join(fixture.challengeRoot, "outside-link"));

  const tree = collector.collectTree(fixture.challengeRoot, { roots: fixture });
  const link = tree.entries.find((item) => item.path === "outside-link");
  assert.equal(link.type, "symlink");
  assert.equal(link.symlink_target, outside);
  assert.equal(tree.entries.some((item) => item.path.includes("outside-secret")), false);
});


test("canonical output is exclusive, byte canonical, and not overwriteable", (t) => {
  const fixture = makeFixture();
  t.after(() => fs.rmSync(fixture.root, { recursive: true, force: true }));
  const value = { schema: collector.OUTPUT_SCHEMA, z: 2, a: 1 };
  const rendered = collector.writeCanonicalExclusive(fixture.outputPath, value);
  assert.equal(rendered, `${collector.canonicalStringify(value)}\n`);
  assert.equal(fs.readFileSync(fixture.outputPath, "utf8"), rendered);
  assert.throws(
    () => collector.writeCanonicalExclusive(fixture.outputPath, value),
    (error) => error.code === "EEXIST",
  );
});


test("failure output is canonical and carries no feature verdict", () => {
  const error = new collector.CollectorInputError("no role accepted", "UNKNOWN_INPUT_FIELD");
  const failure = collector.failureDocument(error);
  const rendered = collector.canonicalStringify(failure);
  assert.equal(rendered, collector.canonicalStringify(JSON.parse(rendered)));
  assert.equal(failure.status, "REJECTED");
  assert.equal(Object.hasOwn(failure, "features"), false);
  assert.equal(Object.hasOwn(failure, "leakage"), false);
});


test("collector source has no network client import or score/ranking implementation", () => {
  const source = fs.readFileSync(path.join(__dirname, "..", "collector.js"), "utf8");
  for (const forbidden of [
    'require("node:http")',
    'require("node:https")',
    'require("node:net")',
    'require("node:dns")',
    "fetch(",
  ]) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
  assert.equal(source.includes("does_not_score_leakage: true"), true);
  assert.equal(source.includes("does_not_rank_treatments: true"), true);
});
