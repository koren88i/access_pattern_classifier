from __future__ import annotations

STYLE = r"""
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
    .export-options {
      display: grid;
      gap: 8px;
      margin: 14px 0 4px;
    }
    .toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
      color: var(--ink);
      font-size: 13px;
      font-weight: 600;
    }
    .toggle input {
      width: auto;
      flex: 0 0 auto;
    }
    .toggle.disabled {
      color: #8a98a8;
    }
    .export-result {
      margin-top: 12px;
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
""".strip("\n")


BODY = r"""
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
      <div class="export-options">
        <label class="toggle" for="indexElastic">
          <input id="indexElastic" type="checkbox">
          <span>Write to Elasticsearch</span>
        </label>
        <label class="toggle disabled" for="includeRawQuery" id="includeRawQueryToggle">
          <input id="includeRawQuery" type="checkbox" disabled>
          <span>Include raw query samples</span>
        </label>
      </div>
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
""".strip("\n")


STATE_SCRIPT = r"""
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
""".strip("\n")


EXPORT_RENDERING_SCRIPT = r"""
    function renderElasticExport(exportPayload) {
      if (!exportPayload) {
        return "";
      }
      const statusClass = exportPayload.status === "ok" ? "" : exportPayload.status === "warning" ? "warning" : "error";
      if (exportPayload.status === "error") {
        return `
          <div class="export-result">
            <h3>Elasticsearch</h3>
            <p class="${statusClass}">${escapeHtml(exportPayload.error || "Export failed")}</p>
          </div>
        `;
      }
      const indices = (exportPayload.indices || []).map(escapeHtml).join(", ");
      const dataViews = (exportPayload.data_views || []).map(escapeHtml).join(", ");
      const warning = exportPayload.warning ? `<p class="warning">${escapeHtml(exportPayload.warning)}</p>` : "";
      return `
        <div class="export-result">
          <h3>Elasticsearch</h3>
          <p class="${statusClass}">Indexed ${escapeHtml(exportPayload.indexed || 0)} documents.</p>
          <p><a href="${escapeHtml(exportPayload.kibana_url)}" target="_blank">Open Kibana</a></p>
          <p>Event time: ${escapeHtml(exportPayload.time_range.start)} to ${escapeHtml(exportPayload.time_range.end)}</p>
          ${indices ? `<p>Indices: ${indices}</p>` : ""}
          ${dataViews ? `<p>Data views: ${dataViews}</p>` : ""}
          ${warning}
        </div>
      `;
    }
""".strip("\n")


MATCHER_SOURCE_SCRIPT = r"""
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
""".strip("\n")


PRIMITIVE_CONTROLS_SCRIPT = r"""
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
""".strip("\n")


RESPONSE_METADATA_SCRIPT = r"""
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
""".strip("\n")


SCENARIO_RUNNER_SCRIPT = r"""
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
      const indexElastic = document.getElementById("indexElastic").checked;
      const includeRawQuery = document.getElementById("includeRawQuery").checked;
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario: document.getElementById("yaml").value,
          index_elastic: indexElastic,
          include_raw_query: includeRawQuery,
          setup_kibana_data_views: indexElastic
        })
      });
      const payload = await response.json();
      if (!response.ok) {
        setStatus(payload.error || "Run failed", "error");
        return;
      }
      const exportStatus = payload.elastic_export?.status;
      const statusClass = exportStatus === "error" ? "error" : exportStatus === "warning" || payload.validation.status === "warning" ? "warning" : "";
      const exportText = exportStatus === "ok"
        ? `; indexed ${payload.elastic_export.indexed} docs`
        : exportStatus === "warning"
          ? "; indexed with Kibana warning"
          : exportStatus === "error"
            ? "; Elasticsearch export failed"
            : "";
      setStatus(`Saved ${payload.run_id}${exportText}`, statusClass);
      const links = payload.artifacts.map(item => `<li><a href="${item.href}" target="_blank">${item.name}</a></li>`).join("");
      const warnings = payload.validation.warnings.length
        ? `<h3>Warnings</h3><pre>${JSON.stringify(payload.validation.warnings, null, 2)}</pre>`
        : "<p>No validation warnings.</p>";
      document.getElementById("result").innerHTML = `
        <h2>Dashboard</h2>
        <pre>${escapeHtml(payload.dashboard)}</pre>
        ${renderElasticExport(payload.elastic_export)}
        ${warnings}
        <h3>Artifacts</h3>
        <ul>${links}</ul>
      `;
    }
""".strip("\n")


INIT_SCRIPT = r"""
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
      document.getElementById("indexElastic").addEventListener("change", event => {
        const enabled = event.target.checked;
        const rawQuery = document.getElementById("includeRawQuery");
        rawQuery.disabled = !enabled;
        if (!enabled) {
          rawQuery.checked = false;
        }
        document.getElementById("includeRawQueryToggle").classList.toggle("disabled", !enabled);
      });
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
""".strip("\n")


SCRIPT = "\n\n".join(
    [
        STATE_SCRIPT,
        EXPORT_RENDERING_SCRIPT,
        MATCHER_SOURCE_SCRIPT,
        PRIMITIVE_CONTROLS_SCRIPT,
        RESPONSE_METADATA_SCRIPT,
        SCENARIO_RUNNER_SCRIPT,
        INIT_SCRIPT,
    ]
)


def render_ui_page() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Workload Simulator</title>
  <style>
{STYLE}
  </style>
</head>
<body>
{BODY}
  <script>
{SCRIPT}
  </script>
</body>
</html>
"""


HTML = render_ui_page()

