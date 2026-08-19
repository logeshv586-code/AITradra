import React, { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Database, KeyRound, Loader2, PlugZap, RefreshCw, Trash2 } from "lucide-react";
import { API_BASE } from "../api_config";

const EMPTY_FORM = {
  name: "",
  provider: "alpha_vantage",
  category: "market_data",
  api_key: "",
  private_key: "",
  endpoint: "",
  auth_mode: "header",
  api_key_name: "X-API-Key",
  api_key_prefix: "",
  query_params_json: "",
  headers_json: "",
  root_path: "",
  price_path: "price",
  change_path: "change_pct",
  open_path: "open",
  high_path: "high",
  low_path: "low",
  volume_path: "volume",
  items_path: "articles",
  headline_path: "title",
  summary_path: "description",
  url_path: "url",
  source_path: "source",
  published_path: "published_at",
};

function parseJsonObject(raw, label) {
  if (!String(raw || "").trim()) return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`${label} must be valid JSON, for example {"symbol":"{ticker}"}.`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed;
}

export default function CustomerConnectionsPanel() {
  const [providers, setProviders] = useState([]);
  const [connections, setConnections] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const selectedProvider = useMemo(
    () => providers.find((item) => item.id === form.provider),
    [providers, form.provider]
  );

  const load = async () => {
    try {
      const [providerResponse, connectionResponse] = await Promise.all([
        fetch(`${API_BASE}/api/customer/providers`),
        fetch(`${API_BASE}/api/customer/connections`),
      ]);
      if (providerResponse.ok) setProviders((await providerResponse.json()).providers || []);
      if (connectionResponse.ok) setConnections((await connectionResponse.json()).connections || []);
    } catch {
      setMessage("Data connections are temporarily unavailable.");
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!selectedProvider || form.provider === "custom_json") return;
    setForm((previous) => ({
      ...previous,
      category: selectedProvider.category,
      name: previous.name || selectedProvider.name,
    }));
  }, [selectedProvider, form.provider]);

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const category = form.provider === "custom_json"
        ? form.category
        : (selectedProvider?.category || form.category);
      const config = {};

      if (form.provider === "custom_json") {
        if (!String(form.endpoint || "").trim()) throw new Error("Enter the custom JSON API endpoint.");
        config.endpoint = form.endpoint.trim();
        config.query_params = parseJsonObject(form.query_params_json, "Query parameters");
        config.headers = parseJsonObject(form.headers_json, "Extra headers");

        if (form.auth_mode === "none") {
          config.api_key_location = "none";
          config.api_key_name = "";
          config.api_key_prefix = "";
        } else if (form.auth_mode === "bearer") {
          config.api_key_location = "header";
          config.api_key_name = "Authorization";
          config.api_key_prefix = "Bearer ";
        } else {
          config.api_key_location = form.auth_mode;
          config.api_key_name = form.api_key_name || (form.auth_mode === "query" ? "apikey" : "X-API-Key");
          config.api_key_prefix = form.api_key_prefix || "";
        }

        config.mapping = category === "news"
          ? {
              root: form.root_path || "",
              items: form.items_path || "articles",
              headline: form.headline_path || "title",
              summary: form.summary_path || "description",
              url: form.url_path || "url",
              source: form.source_path || "source",
              published_at: form.published_path || "published_at",
            }
          : {
              root: form.root_path || "",
              price: form.price_path || "price",
              change_pct: form.change_path || "change_pct",
              open: form.open_path || "open",
              high: form.high_path || "high",
              low: form.low_path || "low",
              volume: form.volume_path || "volume",
            };
      }

      const response = await fetch(`${API_BASE}/api/customer/connections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name || selectedProvider?.name || "My connection",
          provider: form.provider,
          category,
          api_key: form.api_key,
          private_key: form.private_key,
          config,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || "Could not save connection");
      setMessage("Connection saved. AITradra will automatically use it whenever this type of data is requested.");
      setForm({ ...EMPTY_FORM, provider: form.provider, category });
      await load();
    } catch (error) {
      setMessage(error.message || "Could not save connection.");
    } finally {
      setBusy(false);
    }
  };

  const test = async (id) => {
    setMessage("Checking connection…");
    try {
      const response = await fetch(`${API_BASE}/api/customer/connections/${id}/test?ticker=AAPL`, { method: "POST" });
      const data = await response.json();
      setMessage(data.message || (data.ok ? "Connection is working." : "Connection check failed."));
    } catch {
      setMessage("Connection check failed.");
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Remove this connection from this machine?")) return;
    await fetch(`${API_BASE}/api/customer/connections/${id}`, { method: "DELETE" });
    setMessage("Connection removed.");
    await load();
  };

  return (
    <section className="surface-card overflow-hidden">
      <div className="p-5 border-b border-[var(--border-color)] flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="h-9 w-9 rounded-[var(--radius-md)] bg-[var(--accent-bg)] flex items-center justify-center">
            <PlugZap size={17} className="text-[var(--accent)]" />
          </div>
          <div>
            <h2 className="heading-3">Your data & broker connections</h2>
            <p className="text-[11px] text-[var(--text-muted)] mt-1 max-w-2xl">
              Add a preferred market/news API or a trading connection. Credentials are encrypted on this machine and never shown back in the UI.
            </p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-standard h-8 px-3"><RefreshCw size={12} /> Refresh</button>
      </div>

      <div className="p-5 grid grid-cols-1 xl:grid-cols-[0.95fr_1.05fr] gap-5">
        <form onSubmit={save} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4 flex flex-col gap-3">
          <div>
            <div className="text-[12px] font-semibold text-white">Add a connection</div>
            <div className="text-[10px] text-[var(--text-muted)] mt-1">Choose a preset or connect a JSON REST GET API by mapping its authentication, request parameters and response fields.</div>
          </div>
          <select
            value={form.provider}
            onChange={(event) => {
              const provider = providers.find((item) => item.id === event.target.value);
              setForm({ ...EMPTY_FORM, provider: event.target.value, category: provider?.category || "market_data", name: provider?.name || "" });
            }}
            className="input-standard"
          >
            {providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.name} — {provider.category.replace("_", " ")}</option>)}
          </select>

          {form.provider === "custom_json" && (
            <select className="input-standard" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="market_data">Custom market/price API</option>
              <option value="news">Custom news API</option>
            </select>
          )}

          <input className="input-standard" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Connection name" />

          {selectedProvider?.category === "broker" ? (
            <input type="password" className="input-standard" value={form.private_key} onChange={(e) => setForm({ ...form, private_key: e.target.value })} placeholder="Broker private key" autoComplete="off" />
          ) : form.provider !== "custom_json" || form.auth_mode !== "none" ? (
            <input type="password" className="input-standard" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder={selectedProvider?.needs_api_key ? "API key" : "API key / token (optional)"} autoComplete="off" />
          ) : null}

          {form.provider === "custom_json" && (
            <>
              <input className="input-standard" value={form.endpoint} onChange={(e) => setForm({ ...form, endpoint: e.target.value })} placeholder="https://api.example.com/resource/{ticker}" />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <select className="input-standard" value={form.auth_mode} onChange={(e) => setForm({ ...form, auth_mode: e.target.value })}>
                  <option value="none">No API key</option>
                  <option value="bearer">Bearer token</option>
                  <option value="header">API key in header</option>
                  <option value="query">API key in query string</option>
                </select>
                {form.auth_mode !== "none" && form.auth_mode !== "bearer" && <input className="input-standard" value={form.api_key_name} onChange={(e) => setForm({ ...form, api_key_name: e.target.value })} placeholder={form.auth_mode === "query" ? "Query key name, e.g. apikey" : "Header name, e.g. X-API-Key"} />}
                {form.auth_mode === "header" && <input className="input-standard sm:col-span-2" value={form.api_key_prefix} onChange={(e) => setForm({ ...form, api_key_prefix: e.target.value })} placeholder="Optional key prefix, e.g. Token " />}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <textarea className="input-standard min-h-[82px] font-mono text-[10px]" value={form.query_params_json} onChange={(e) => setForm({ ...form, query_params_json: e.target.value })} placeholder={'Optional query JSON\n{"symbol":"{ticker}","region":"US"}'} />
                <textarea className="input-standard min-h-[82px] font-mono text-[10px]" value={form.headers_json} onChange={(e) => setForm({ ...form, headers_json: e.target.value })} placeholder={'Optional headers JSON\n{"Accept":"application/json"}'} />
              </div>

              <input className="input-standard" value={form.root_path} onChange={(e) => setForm({ ...form, root_path: e.target.value })} placeholder="Optional response root path, e.g. data.quote" />

              {form.category === "news" ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input className="input-standard" value={form.items_path} onChange={(e) => setForm({ ...form, items_path: e.target.value })} placeholder="Articles array path" />
                  <input className="input-standard" value={form.headline_path} onChange={(e) => setForm({ ...form, headline_path: e.target.value })} placeholder="Headline field" />
                  <input className="input-standard" value={form.summary_path} onChange={(e) => setForm({ ...form, summary_path: e.target.value })} placeholder="Summary field" />
                  <input className="input-standard" value={form.url_path} onChange={(e) => setForm({ ...form, url_path: e.target.value })} placeholder="URL field" />
                  <input className="input-standard" value={form.source_path} onChange={(e) => setForm({ ...form, source_path: e.target.value })} placeholder="Source field" />
                  <input className="input-standard" value={form.published_path} onChange={(e) => setForm({ ...form, published_path: e.target.value })} placeholder="Published date field" />
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input className="input-standard" value={form.price_path} onChange={(e) => setForm({ ...form, price_path: e.target.value })} placeholder="Price field path" />
                  <input className="input-standard" value={form.change_path} onChange={(e) => setForm({ ...form, change_path: e.target.value })} placeholder="Change % field path" />
                  <input className="input-standard" value={form.open_path} onChange={(e) => setForm({ ...form, open_path: e.target.value })} placeholder="Open field path" />
                  <input className="input-standard" value={form.high_path} onChange={(e) => setForm({ ...form, high_path: e.target.value })} placeholder="High field path" />
                  <input className="input-standard" value={form.low_path} onChange={(e) => setForm({ ...form, low_path: e.target.value })} placeholder="Low field path" />
                  <input className="input-standard" value={form.volume_path} onChange={(e) => setForm({ ...form, volume_path: e.target.value })} placeholder="Volume field path" />
                </div>
              )}
              <p className="text-[9px] text-[var(--text-muted)] leading-relaxed">Use <code>{"{ticker}"}</code> in the endpoint, query values or header values. Nested JSON paths use dots, for example <code>data.quote.price</code>. Custom connections currently expect a GET endpoint returning JSON.</p>
            </>
          )}

          {selectedProvider?.description && <p className="text-[10px] text-[var(--text-muted)] leading-relaxed">{selectedProvider.description}</p>}
          <button disabled={busy} className="btn-primary py-2.5 text-[12px]">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <KeyRound size={13} />} Save connection
          </button>
          {message && <div className="text-[11px] text-[var(--text-muted)] leading-relaxed">{message}</div>}
        </form>

        <div className="flex flex-col gap-3">
          {connections.length ? connections.map((connection) => (
            <div key={connection.id} className="rounded-[var(--radius-md)] border border-[var(--border-color)] bg-[#171b22] p-4 flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Database size={14} className="text-[var(--accent)]" />
                  <span className="text-[12px] font-semibold text-white truncate">{connection.name}</span>
                  {connection.has_credentials && <CheckCircle2 size={13} className="text-[var(--positive)]" />}
                </div>
                <div className="text-[10px] text-[var(--text-muted)] mt-1">
                  {connection.provider.replace("_", " ")} • {connection.category.replace("_", " ")} • {connection.enabled ? "enabled" : "disabled"}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button type="button" className="btn-standard h-8 px-3" onClick={() => test(connection.id)}>Test</button>
                <button type="button" className="btn-standard h-8 w-8 !px-0 text-[var(--negative)]" onClick={() => remove(connection.id)} aria-label="Remove connection"><Trash2 size={13} /></button>
              </div>
            </div>
          )) : (
            <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--border-color)] p-8 text-center text-[11px] text-[var(--text-muted)]">
              No personal API is required. AITradra will continue using its built-in public/open data sources until you add one.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
