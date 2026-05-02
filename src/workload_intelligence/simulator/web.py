from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from workload_intelligence.simulator.capabilities import capability_payload
from workload_intelligence.simulator.matcher_source import matcher_source_for
from workload_intelligence.simulator.runner import DEFAULT_OUTPUT_ROOT, run_scenario_text
from workload_intelligence.simulator.scenario import ScenarioValidationError


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Workload Simulator</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #18202a;
      --muted: #607086;
      --line: #d9e0e8;
      --fill: #f6f8fb;
      --accent: #1d7f68;
      --accent-dark: #125c4c;
      --warn: #9a4f00;
      --bad: #9b1c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Segoe UI, system-ui, -apple-system, sans-serif;
      color: var(--ink);
      background: #ffffff;
    }
    header {
      padding: 18px 24px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.2;
      font-weight: 650;
    }
    main {
      display: grid;
      grid-template-columns: minmax(300px, 390px) minmax(360px, 0.9fr) minmax(400px, 1.1fr);
      min-height: calc(100vh - 62px);
    }
    aside {
      padding: 18px;
      border-right: 1px solid var(--line);
      background: var(--fill);
      overflow: auto;
    }
    section {
      padding: 18px;
      min-width: 0;
      overflow: auto;
    }
    label {
      display: block;
      font-size: 12px;
      font-weight: 650;
      color: var(--muted);
      margin: 14px 0 5px;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
      background: #ffffff;
      color: var(--ink);
    }
    textarea {
      min-height: 560px;
      resize: vertical;
      font-family: Consolas, ui-monospace, monospace;
      font-size: 13px;
      line-height: 1.45;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .primitives {
      display: grid;
      gap: 6px;
      margin-top: 8px;
    }
    .primitive {
      display: grid;
      grid-template-columns: minmax(128px, 150px) 1fr;
      gap: 10px;
      align-items: center;
      padding: 7px 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      font-size: 13px;
      min-height: 34px;
      cursor: pointer;
    }
    .primitive-name {
      display: flex;
      gap: 7px;
      align-items: center;
      color: var(--ink);
      min-width: 0;
    }
    .primitive-name input {
      width: auto;
      flex: 0 0 auto;
    }
    .primitive-description {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .primitive.disabled {
      background: #edf1f5;
      cursor: default;
    }
    .primitive.disabled .primitive-name,
    .primitive.disabled .primitive-description {
      color: #8a98a8;
    }
    .primitive.selected {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px rgba(29, 127, 104, 0.15);
    }
    .response-signals {
      display: grid;
      gap: 6px;
      margin-top: 8px;
    }
    .response-signal {
      display: grid;
      grid-template-columns: minmax(128px, 150px) 1fr;
      gap: 10px;
      padding: 7px 8px;
      border: 1px dashed var(--line);
      border-radius: 6px;
      background: #ffffff;
      color: var(--muted);
      font-size: 13px;
      min-height: 34px;
    }
    .response-signal-name {
      font-weight: 650;
      color: var(--muted);
    }
    .response-signal-description {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .response-metadata {
      display: grid;
      gap: 8px;
      margin-top: 8px;
    }
    .response-metric {
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
    }
    .response-metric-header {
      display: grid;
      grid-template-columns: minmax(120px, 1fr) minmax(120px, 150px);
      gap: 8px;
      align-items: center;
    }
    .response-metric-title {
      font-size: 13px;
      font-weight: 650;
      color: var(--ink);
    }
    .response-metric select,
    .response-field-grid input {
      padding: 6px 8px;
    }
    .response-field-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 8px;
    }
    .response-field-grid label {
      margin: 0 0 4px;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 9px 12px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      background: var(--accent);
      color: white;
    }
    button.secondary {
      background: #e5ebf2;
      color: var(--ink);
    }
    button:hover { background: var(--accent-dark); }
    button.secondary:hover { background: #d6dee8; }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 14px 0;
    }
    .result {
      margin-top: 16px;
      border-top: 1px solid var(--line);
      padding-top: 14px;
    }
    pre {
      overflow: auto;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f8fafc;
      line-height: 1.45;
    }
    .status {
      font-weight: 650;
      color: var(--muted);
      min-height: 24px;
    }
    .warning { color: var(--warn); }
    .error { color: var(--bad); }
    a { color: #176f8f; }
    .matcher {
      border-left: 1px solid var(--line);
      background: #fbfcfe;
    }
    .matcher-source {
      display: grid;
      gap: 12px;
    }
    .source-block {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      overflow: hidden;
    }
    .source-block-header {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    .source-block pre {
      margin: 0;
      border: 0;
      border-radius: 0;
      max-height: 320px;
      font-size: 12px;
    }
    .json-line {
      display: block;
      min-height: 1.45em;
      margin: 0 -4px;
      padding: 0 4px;
      border-left: 3px solid transparent;
      white-space: pre;
    }
    .json-line.highlight {
      border-left-color: var(--accent);
      background: #dff4ee;
    }
    .json-key {
      color: #245b8a;
    }
    .json-string {
      color: #7a3f0b;
    }
    .json-number,
    .json-boolean,
    .json-null {
      color: #7c2d8f;
    }
    .source-empty {
      color: var(--muted);
      margin: 0;
    }
    .field-help {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .source-group-title {
      margin: 8px 0 0;
      font-size: 13px;
      font-weight: 700;
      color: var(--ink);
    }
    details.source-details {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      overflow: hidden;
    }
    details.source-details > summary {
      cursor: pointer;
      padding: 9px 10px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    details.source-details .source-block {
      border-left: 0;
      border-right: 0;
      border-bottom: 0;
      border-radius: 0;
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      aside,
      .matcher {
        border-right: 0;
        border-left: 0;
        border-bottom: 1px solid var(--line);
      }
      textarea { min-height: 360px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Workload Simulator</h1>
    <div class="status" id="status"></div>
  </header>
  <main>
    <aside>
      <div class="grid">
        <div>
          <label for="platform">Platform</label>
          <select id="platform"></select>
        </div>
        <div>
          <label for="events">Events</label>
          <input id="events" type="number" min="1" value="100">
        </div>
      </div>
      <label for="name">Scenario</label>
      <input id="name" value="simulated_workload">
      <label for="system">System</label>
      <input id="system" value="demo-api">
      <div class="grid">
        <div>
          <label for="customer">Customer</label>
          <input id="customer" value="acme">
        </div>
        <div>
          <label for="database">Database / Index</label>
          <input id="database" value="orders">
        </div>
      </div>
      <div class="grid">
        <div>
          <label for="seed">Seed</label>
          <input id="seed" type="number" value="42">
        </div>
        <div>
          <label for="share">Shape Share</label>
          <input id="share" type="number" min="1" max="100" value="100">
          <p class="field-help">This control edits one query shape. Add more shapes directly in Scenario YAML.</p>
        </div>
      </div>
      <label>Primitive Bundle</label>
      <div class="primitives" id="primitives"></div>
      <label>Response-Derived Signals</label>
      <div class="response-signals" id="responseSignals"></div>
      <label>Response Metadata</label>
      <div class="response-metadata" id="responseMetadata"></div>
      <div class="actions">
        <button id="build" class="secondary">Build YAML</button>
        <button id="run">Run Scenario</button>
      </div>
    </aside>
    <section class="matcher">
      <label>Matcher Source</label>
      <div class="matcher-source" id="matcherSource"></div>
    </section>
    <section>
      <label for="yaml">Scenario YAML</label>
      <textarea id="yaml"></textarea>
      <div class="result" id="result"></div>
    </section>
  </main>
  <script>
    let capabilities = null;
    let selectedPrimitive = null;
    let matcherRequest = 0;

    function setStatus(message, cls = "") {
      const el = document.getElementById("status");
      el.textContent = message;
      el.className = "status " + cls;
    }

    function checkedPrimitives() {
      return Array.from(document.querySelectorAll(".primitive input:checked")).map(input => input.value);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function renderPrimitiveSelection() {
      document.querySelectorAll(".primitive").forEach(item => {
        const input = item.querySelector("input");
        item.classList.toggle("selected", input?.checked && item.dataset.primitive === selectedPrimitive);
      });
    }

    function activePrimitive() {
      const checked = checkedPrimitives();
      if (!checked.length) return "";
      if (selectedPrimitive && checked.includes(selectedPrimitive)) {
        return selectedPrimitive;
      }
      return checked[0];
    }

    async function loadMatcherSource() {
      const platform = document.getElementById("platform").value;
      const primitive = activePrimitive();
      const box = document.getElementById("matcherSource");
      if (!platform || !primitive) {
        selectedPrimitive = null;
        renderPrimitiveSelection();
        box.innerHTML = '<p class="source-empty">Tick a primitive flag to inspect its generated query, normalized matcher input, and matching rule.</p>';
        return;
      }
      selectedPrimitive = primitive;
      renderPrimitiveSelection();
      const requestId = ++matcherRequest;
      box.innerHTML = '<p class="source-empty">Loading source...</p>';
      const response = await fetch(
        `/api/matcher-source?platform=${encodeURIComponent(platform)}&primitive=${encodeURIComponent(primitive)}&primitives=${encodeURIComponent(checkedPrimitives().join(","))}`
      );
      const payload = await response.json();
      if (requestId !== matcherRequest) return;
      if (!response.ok) {
        box.innerHTML = `<p class="source-empty error">${escapeHtml(payload.error || "source unavailable")}</p>`;
        return;
      }
      if (payload.inactive) {
        box.innerHTML = '<p class="source-empty">Tick a primitive flag to inspect its generated query, normalized matcher input, and matching rule.</p>';
        return;
      }
      renderMatcherSource(payload);
    }

    function sourceBlock(title, path, source) {
      return `
        <div class="source-block">
          <div class="source-block-header">
            <span>${escapeHtml(title)}</span>
            <span>${escapeHtml(path)}</span>
          </div>
          <pre><code>${escapeHtml(source)}</code></pre>
        </div>
      `;
    }

    function htmlSourceBlock(title, path, html) {
      return `
        <div class="source-block">
          <div class="source-block-header">
            <span>${escapeHtml(title)}</span>
            <span>${escapeHtml(path)}</span>
          </div>
          <pre><code>${html}</code></pre>
        </div>
      `;
    }

    function relevantMatcherPaths(payload) {
      const paths = new Set();
      for (const rule of payload.sample.relevant_matcher_fields || []) {
        for (const condition of rule.conditions || []) {
          for (const field of condition.fields || []) {
            if (field.path && field.path !== "$") paths.add(field.path);
          }
        }
      }
      return paths;
    }

    function jsonToken(value) {
      if (typeof value === "string") {
        return `<span class="json-string">${escapeHtml(JSON.stringify(value))}</span>`;
      }
      if (typeof value === "number") {
        return `<span class="json-number">${escapeHtml(String(value))}</span>`;
      }
      if (typeof value === "boolean") {
        return `<span class="json-boolean">${value}</span>`;
      }
      if (value === null) {
        return '<span class="json-null">null</span>';
      }
      return escapeHtml(JSON.stringify(value));
    }

    function inlineJson(value) {
      return escapeHtml(JSON.stringify(value));
    }

    function jsonLine(content, highlighted = false) {
      return `<span class="json-line${highlighted ? " highlight" : ""}">${content}</span>`;
    }

    function renderJsonProperty(key, value, path, indent, isLast, highlightPaths) {
      const pad = " ".repeat(indent);
      const comma = isLast ? "" : ",";
      const keyHtml = `<span class="json-key">${escapeHtml(JSON.stringify(key))}</span>: `;
      const highlighted = highlightPaths.has(path);
      if (highlighted) {
        return [jsonLine(`${pad}${keyHtml}${inlineJson(value)}${comma}`, true)];
      }
      if (Array.isArray(value)) {
        if (!value.length) return [jsonLine(`${pad}${keyHtml}[]${comma}`)];
        const lines = [jsonLine(`${pad}${keyHtml}[`)];
        value.forEach((item, index) => {
          lines.push(...renderJsonValue(item, `${path}.${index}`, indent + 2, index === value.length - 1, highlightPaths));
        });
        lines.push(jsonLine(`${pad}]${comma}`));
        return lines;
      }
      if (value && typeof value === "object") {
        const entries = Object.entries(value);
        if (!entries.length) return [jsonLine(`${pad}${keyHtml}{}${comma}`)];
        const lines = [jsonLine(`${pad}${keyHtml}{`)];
        entries.forEach(([childKey, childValue], index) => {
          lines.push(...renderJsonProperty(childKey, childValue, `${path}.${childKey}`, indent + 2, index === entries.length - 1, highlightPaths));
        });
        lines.push(jsonLine(`${pad}}${comma}`));
        return lines;
      }
      return [jsonLine(`${pad}${keyHtml}${jsonToken(value)}${comma}`)];
    }

    function renderJsonValue(value, path, indent, isLast, highlightPaths) {
      const pad = " ".repeat(indent);
      const comma = isLast ? "" : ",";
      if (Array.isArray(value)) {
        if (!value.length) return [jsonLine(`${pad}[]${comma}`, highlightPaths.has(path))];
        const highlighted = highlightPaths.has(path);
        if (highlighted) return [jsonLine(`${pad}${inlineJson(value)}${comma}`, true)];
        const lines = [jsonLine(`${pad}[`)];
        value.forEach((item, index) => {
          lines.push(...renderJsonValue(item, `${path}.${index}`, indent + 2, index === value.length - 1, highlightPaths));
        });
        lines.push(jsonLine(`${pad}]${comma}`));
        return lines;
      }
      if (value && typeof value === "object") {
        const highlighted = highlightPaths.has(path);
        if (highlighted) return [jsonLine(`${pad}${inlineJson(value)}${comma}`, true)];
        const entries = Object.entries(value);
        if (!entries.length) return [jsonLine(`${pad}{}${comma}`)];
        const lines = [jsonLine(`${pad}{`)];
        entries.forEach(([key, childValue], index) => {
          lines.push(...renderJsonProperty(key, childValue, `${path}.${key}`, indent + 2, index === entries.length - 1, highlightPaths));
        });
        lines.push(jsonLine(`${pad}}${comma}`));
        return lines;
      }
      return [jsonLine(`${pad}${jsonToken(value)}${comma}`, highlightPaths.has(path))];
    }

    function highlightedJson(value, highlightPaths) {
      return renderJsonValue(value, "$", 0, true, highlightPaths).join("");
    }

    function renderMatcherSource(payload) {
      const box = document.getElementById("matcherSource");
      const highlightPaths = relevantMatcherPaths(payload);
      const generatedOperation = sourceBlock(
        "Generated platform query",
        "simulator runtime sample",
        JSON.stringify(payload.sample.generated_operation, null, 2)
      );
      const relevantFields = sourceBlock(
        `Rule condition trace for ${payload.primitive}`,
        "derived from primitive rule conditions",
        JSON.stringify(payload.sample.relevant_matcher_fields, null, 2)
      );
      const normalizedInput = htmlSourceBlock(
        "Normalized matcher input",
        "highlighted fields are read by the selected primitive rule",
        highlightedJson(payload.sample.normalized_matcher_input, highlightPaths)
      );
      const selectedSignal = sourceBlock(
        `Observed signal: ${payload.primitive}`,
        "primitive extractor output",
        JSON.stringify(payload.sample.selected_primitive_signal, null, 2)
      );
      const ruleBlocks = payload.rules.map(rule => sourceBlock(rule.id, rule.path, rule.source)).join("");
      const codeBlocks = payload.code
        .map(block => sourceBlock(`${block.role}: ${block.name}`, block.path, block.source))
        .join("");
      const emptyRules = payload.rules.length
        ? ""
        : `<p class="source-empty">No primitive rule is declared for ${escapeHtml(payload.platform)} / ${escapeHtml(payload.primitive)}.</p>`;
      box.innerHTML = `
        <div class="source-group-title">Runtime Objects</div>
        ${generatedOperation}
        ${relevantFields}
        ${normalizedInput}
        ${selectedSignal}
        <div class="source-group-title">Primitive Rule</div>
        ${emptyRules}
        ${ruleBlocks}
        <details class="source-details">
          <summary>Advanced source code</summary>
          ${codeBlocks}
        </details>
      `;
    }

    function renderPrimitives() {
      const platform = document.getElementById("platform").value;
      const box = document.getElementById("primitives");
      box.innerHTML = "";
      if (!capabilities || !platform) return;
      for (const primitive of capabilities.platforms[platform].primitives) {
        const item = document.createElement("div");
        item.className = "primitive" + (primitive.supported ? "" : " disabled");
        item.dataset.primitive = primitive.name;
        if (primitive.reason) item.title = primitive.reason;
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = primitive.name;
        input.disabled = !primitive.supported;
        input.addEventListener("click", event => event.stopPropagation());
        input.addEventListener("change", () => {
          selectedPrimitive = input.checked ? primitive.name : null;
          renderPrimitiveSelection();
          buildYaml();
          loadMatcherSource();
        });
        item.addEventListener("click", () => {
          if (!input.checked || input.disabled) return;
          selectedPrimitive = primitive.name;
          renderPrimitiveSelection();
          loadMatcherSource();
        });
        const name = document.createElement("span");
        name.className = "primitive-name";
        name.appendChild(input);
        name.appendChild(document.createTextNode(primitive.name));
        const description = document.createElement("span");
        description.className = "primitive-description";
        description.textContent = primitive.description || primitive.reason || "";
        item.appendChild(name);
        item.appendChild(description);
        box.appendChild(item);
      }
      if (!selectedPrimitive || !checkedPrimitives().includes(selectedPrimitive)) {
        selectedPrimitive = activePrimitive();
      }
      renderPrimitiveSelection();
      renderResponseSignals();
      loadMatcherSource();
    }

    function renderResponseSignals() {
      const platform = document.getElementById("platform").value;
      const box = document.getElementById("responseSignals");
      box.innerHTML = "";
      if (!capabilities || !platform) return;
      for (const signal of capabilities.platforms[platform].response_derived_primitives || []) {
        const item = document.createElement("div");
        item.className = "response-signal";
        if (signal.reason) item.title = signal.reason;
        const name = document.createElement("span");
        name.className = "response-signal-name";
        name.textContent = signal.name;
        const description = document.createElement("span");
        description.className = "response-signal-description";
        description.textContent = signal.description || signal.reason || "";
        item.appendChild(name);
        item.appendChild(description);
        box.appendChild(item);
      }
    }

    function responseDistribution(name) {
      return (capabilities.response_metadata.distributions || []).find(item => item.name === name);
    }

    function responseMetric(name) {
      return (capabilities.response_metadata.metrics || []).find(item => item.name === name);
    }

    function responseFieldId(metricName, fieldName) {
      return `response-${metricName}-${fieldName}`;
    }

    function renderResponseFields(metricName) {
      const metric = responseMetric(metricName);
      const select = document.querySelector(`select[data-response-distribution="${metricName}"]`);
      const fieldsBox = document.getElementById(`responseFields-${metricName}`);
      if (!metric || !select || !fieldsBox) return;
      const distribution = responseDistribution(select.value);
      if (!distribution) return;
      const defaults = (metric.defaults && metric.defaults[select.value]) || {};
      fieldsBox.innerHTML = "";
      for (const field of distribution.fields || []) {
        const wrapper = document.createElement("div");
        const label = document.createElement("label");
        label.htmlFor = responseFieldId(metricName, field.name);
        label.textContent = field.display_name || field.name;
        const input = document.createElement("input");
        input.id = responseFieldId(metricName, field.name);
        input.type = "number";
        input.min = "0";
        input.step = field.step || "1";
        input.value = defaults[field.name] ?? 0;
        input.dataset.responseMetric = metricName;
        input.dataset.responseField = field.name;
        wrapper.appendChild(label);
        wrapper.appendChild(input);
        fieldsBox.appendChild(wrapper);
      }
    }

    function renderResponseMetadataControls() {
      const box = document.getElementById("responseMetadata");
      box.innerHTML = "";
      if (!capabilities || !capabilities.response_metadata) return;
      const config = capabilities.response_metadata;
      for (const metric of config.metrics || []) {
        const metricBox = document.createElement("div");
        metricBox.className = "response-metric";
        const header = document.createElement("div");
        header.className = "response-metric-header";
        const title = document.createElement("div");
        title.className = "response-metric-title";
        title.textContent = metric.display_name || metric.name;
        const select = document.createElement("select");
        select.dataset.responseDistribution = metric.name;
        for (const distribution of config.distributions || []) {
          const option = document.createElement("option");
          option.value = distribution.name;
          option.textContent = distribution.display_name || distribution.name;
          select.appendChild(option);
        }
        select.value = metric.default_distribution || select.options[0]?.value || "";
        select.addEventListener("change", () => renderResponseFields(metric.name));
        header.appendChild(title);
        header.appendChild(select);
        const fields = document.createElement("div");
        fields.className = "response-field-grid";
        fields.id = `responseFields-${metric.name}`;
        metricBox.appendChild(header);
        metricBox.appendChild(fields);
        box.appendChild(metricBox);
        renderResponseFields(metric.name);
      }
    }

    function responseMetadataYamlLines() {
      const lines = ["responses:"];
      for (const metric of capabilities.response_metadata.metrics || []) {
        const select = document.querySelector(`select[data-response-distribution="${metric.name}"]`);
        const distributionName = select?.value || metric.default_distribution;
        const distribution = responseDistribution(distributionName);
        if (!distribution) continue;
        const parts = [`distribution: ${distributionName}`];
        for (const field of distribution.fields || []) {
          const input = document.querySelector(
            `input[data-response-metric="${metric.name}"][data-response-field="${field.name}"]`
          );
          parts.push(`${field.name}: ${input?.value || 0}`);
        }
        lines.push(`  ${metric.name}: { ${parts.join(", ")} }`);
      }
      return lines;
    }

    function buildYaml() {
      const primitives = checkedPrimitives();
      const platform = document.getElementById("platform").value;
      const name = document.getElementById("name").value || "simulated_workload";
      const db = document.getElementById("database").value || (platform === "elasticsearch" ? "events" : "orders");
      const lines = [
        `name: ${name}`,
        `seed: ${document.getElementById("seed").value || 42}`,
        "target:",
        `  platform: ${platform}`,
        `  system_id: ${document.getElementById("system").value || "demo-api"}`,
        `  customer_id: ${document.getElementById("customer").value || "acme"}`,
        `  database_or_index: ${db}`,
        "time_range:",
        "  start: \"2026-04-30T00:00:00Z\"",
        "  end: \"2026-05-01T00:00:00Z\"",
        `events: ${document.getElementById("events").value || 100}`,
        ...responseMetadataYamlLines(),
        "query_shapes:",
        "  - name: shape_1",
        `    share: ${document.getElementById("share").value || 100}`,
        `    primitives: [${primitives.join(", ")}]`
      ];
      document.getElementById("yaml").value = lines.join("\n");
    }

    async function runScenario() {
      setStatus("Running...");
      document.getElementById("result").innerHTML = "";
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: document.getElementById("yaml").value
      });
      const payload = await response.json();
      if (!response.ok) {
        setStatus(payload.error || "Run failed", "error");
        return;
      }
      setStatus(`Saved ${payload.run_id}`, payload.validation.status === "warning" ? "warning" : "");
      const links = payload.artifacts.map(item => `<li><a href="${item.href}" target="_blank">${item.name}</a></li>`).join("");
      const warnings = payload.validation.warnings.length
        ? `<h3>Warnings</h3><pre>${JSON.stringify(payload.validation.warnings, null, 2)}</pre>`
        : "<p>No validation warnings.</p>";
      document.getElementById("result").innerHTML = `
        <h2>Dashboard</h2>
        <pre>${payload.dashboard.replaceAll("&", "&amp;").replaceAll("<", "&lt;")}</pre>
        ${warnings}
        <h3>Artifacts</h3>
        <ul>${links}</ul>
      `;
    }

    async function init() {
      capabilities = await (await fetch("/api/capabilities")).json();
      const platformSelect = document.getElementById("platform");
      for (const platform of Object.keys(capabilities.platforms)) {
        const option = document.createElement("option");
        option.value = platform;
        option.textContent = capabilities.platforms[platform].display_name;
        platformSelect.appendChild(option);
      }
      platformSelect.value = "postgres";
      platformSelect.addEventListener("change", () => {
        selectedPrimitive = null;
        renderPrimitives();
        buildYaml();
      });
      document.getElementById("build").addEventListener("click", buildYaml);
      document.getElementById("run").addEventListener("click", runScenario);
      renderResponseMetadataControls();
      renderPrimitives();
      for (const name of ["text_search", "sort_paginate"]) {
        const input = document.querySelector(`.primitive input[value="${name}"]`);
        if (input && !input.disabled) input.checked = true;
      }
      selectedPrimitive = "text_search";
      renderPrimitiveSelection();
      buildYaml();
      loadMatcherSource();
      setStatus("Ready");
    }
    init().catch(error => setStatus(error.message, "error"));
  </script>
</body>
</html>
"""


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _text_response(handler: BaseHTTPRequestHandler, status: int, text: str, content_type: str = "text/plain") -> None:
    encoded = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", f"{content_type}; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def make_handler(output_root: Path):
    root = output_root.resolve()

    class SimulatorHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                _text_response(self, HTTPStatus.OK, HTML, content_type="text/html")
                return
            if self.path == "/api/capabilities":
                _json_response(self, HTTPStatus.OK, capability_payload())
                return
            if self.path.startswith("/api/matcher-source"):
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                platform = query.get("platform", [""])[0]
                primitive = query.get("primitive", [""])[0]
                selected_primitives = [
                    item
                    for item in query.get("primitives", [""])[0].split(",")
                    if item
                ]
                if not platform or not primitive:
                    _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "platform and primitive are required"})
                    return
                _json_response(self, HTTPStatus.OK, matcher_source_for(platform, primitive, selected_primitives))
                return
            if self.path.startswith("/runs/"):
                self._serve_artifact()
                return
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/api/run":
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            scenario_text = self.rfile.read(length).decode("utf-8")
            try:
                result = run_scenario_text(scenario_text, output_root=root)
            except ScenarioValidationError as exc:
                _json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            artifacts = [
                {"name": name, "href": f"/runs/{result['run_id']}/{name}"}
                for name in (
                    "scenario.yaml",
                    "events.json",
                    "profiles.json",
                    "report.json",
                    "dashboard.txt",
                    "platform.txt",
                    "templates.txt",
                    "primitive-weights.txt",
                    "validation.json",
                )
            ]
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "run_id": result["run_id"],
                    "dashboard": result["dashboard"],
                    "validation": result["validation"],
                    "artifacts": artifacts,
                },
            )

        def _serve_artifact(self) -> None:
            relative = unquote(self.path.removeprefix("/runs/"))
            candidate = (root / relative).resolve()
            if root not in candidate.parents:
                _json_response(self, HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            if not candidate.is_file():
                _json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            content_type = "application/json" if candidate.suffix == ".json" else "text/plain"
            _text_response(self, HTTPStatus.OK, candidate.read_text(encoding="utf-8"), content_type=content_type)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return SimulatorHandler


def serve_ui(
    host: str = "127.0.0.1",
    port: int = 8765,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), make_handler(output_root))
    print(f"Workload simulator UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
