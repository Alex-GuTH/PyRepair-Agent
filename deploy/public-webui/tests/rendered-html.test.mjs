import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the public PyRepair demo console", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>PyRepair Agent Public Demo<\/title>/i);
  assert.match(html, /AI4SE Coding Agent Harness/);
  assert.match(html, /Run feedback loop/);
  assert.match(html, /Run guardrail demo/);
  assert.match(html, /mock-only/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Your site is taking shape/);
});

test("public demo source stays mock-only", async () => {
  const [page, consoleSource] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/PublicDemoConsole.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(page, /PublicDemoConsole/);
  assert.match(consoleSource, /run-public-feedback-loop/);
  assert.match(consoleSource, /run-public-guardrail/);
  assert.match(consoleSource, /no host paths/);
  assert.doesNotMatch(consoleSource, /fetch\(|localhost|127\.0\.0\.1|API key|process\.env/);
});
