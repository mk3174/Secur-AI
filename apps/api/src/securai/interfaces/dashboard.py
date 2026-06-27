"""Embedded MVP dashboard (single-file, zero-build).

Phase 1 ships a self-contained dashboard so the platform is usable end-to-end
without a separate frontend build. The SAD's React/Vite SPA replaces this in a
later phase; the API it consumes stays identical.
"""

from __future__ import annotations

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en" class="dark">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SecurAI · AI Gateway</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body { background: #0b0f1a; color: #e5e7eb; font-family: ui-sans-serif, system-ui, sans-serif; }
  .card { background: #131a2a; border: 1px solid #1f2937; border-radius: 14px; }
  .btn { background: #4f46e5; transition: .15s; }
  .btn:hover { background: #6366f1; }
  input { background:#0b1220; border:1px solid #243049; color:#e5e7eb; }
  code { color:#a5b4fc; }
  th { color:#94a3b8; font-weight:600; }
</style>
</head>
<body class="min-h-screen">
<div class="max-w-6xl mx-auto p-6">
  <header class="flex items-center justify-between mb-8">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center font-bold">S</div>
      <div>
        <h1 class="text-xl font-bold">SecurAI</h1>
        <p class="text-xs text-slate-400">Enterprise AI Gateway · Phase 1 MVP</p>
      </div>
    </div>
    <button id="logoutBtn" class="hidden text-sm text-slate-400 hover:text-white">Sign out</button>
  </header>

  <section id="loginView" class="max-w-md mx-auto card p-6">
    <h2 class="text-lg font-semibold mb-4">Sign in</h2>
    <label class="block text-sm mb-1 text-slate-400">Email</label>
    <input id="email" class="w-full rounded-lg px-3 py-2 mb-3" value="admin@securai.local" />
    <label class="block text-sm mb-1 text-slate-400">Password</label>
    <input id="password" type="password" class="w-full rounded-lg px-3 py-2 mb-4" value="admin12345" />
    <button id="loginBtn" class="btn w-full rounded-lg py-2 font-medium">Sign in</button>
    <p id="loginErr" class="text-red-400 text-sm mt-3"></p>
    <p class="text-xs text-slate-500 mt-4">Default credentials are created on first run (configurable).</p>
  </section>

  <main id="appView" class="hidden space-y-6">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4" id="statCards"></div>

    <div class="grid md:grid-cols-2 gap-6">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold">Projects</h2>
        </div>
        <div class="flex gap-2 mb-4">
          <input id="projName" placeholder="New project name" class="flex-1 rounded-lg px-3 py-2" />
          <button id="addProj" class="btn rounded-lg px-4">Add</button>
        </div>
        <div id="projects" class="space-y-2 text-sm"></div>
      </div>

      <div class="card p-5">
        <h2 class="font-semibold mb-3">API keys</h2>
        <p class="text-xs text-slate-400 mb-3">Select a project to manage keys.</p>
        <div class="flex gap-2 mb-4">
          <input id="keyName" placeholder="Key name" class="flex-1 rounded-lg px-3 py-2" />
          <button id="addKey" class="btn rounded-lg px-4">Create key</button>
        </div>
        <p id="newKey" class="hidden text-xs bg-emerald-900/40 border border-emerald-700 rounded-lg p-3 mb-3 break-all"></p>
        <div id="keys" class="space-y-2 text-sm"></div>
      </div>
    </div>

    <div class="card p-5">
      <h2 class="font-semibold mb-3">Recent requests</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="text-left border-b border-slate-700">
            <th class="py-2">Time</th><th>Model</th><th>Status</th><th>Tokens</th><th>Latency</th><th>Request ID</th>
          </tr></thead>
          <tbody id="logs"></tbody>
        </table>
      </div>
    </div>
  </main>
</div>

<script>
const API = "/api/v1";
let token = localStorage.getItem("securai_token");
let activeProject = null;

function authHeaders() { return { "Content-Type": "application/json", "Authorization": "Bearer " + token }; }
async function api(path, opts={}) {
  const res = await fetch(API + path, { headers: authHeaders(), ...opts });
  if (res.status === 401) { logout(); throw new Error("unauthorized"); }
  return res;
}
function show(view) {
  document.getElementById("loginView").classList.toggle("hidden", view !== "login");
  document.getElementById("appView").classList.toggle("hidden", view !== "app");
  document.getElementById("logoutBtn").classList.toggle("hidden", view !== "app");
}
function logout() { localStorage.removeItem("securai_token"); token = null; show("login"); }

document.getElementById("logoutBtn").onclick = logout;
document.getElementById("loginBtn").onclick = async () => {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const res = await fetch(API + "/auth/login", {
    method: "POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({email, password})
  });
  if (!res.ok) { document.getElementById("loginErr").textContent = "Invalid credentials"; return; }
  const data = await res.json();
  token = data.access_token; localStorage.setItem("securai_token", token);
  show("app"); refresh();
};

async function refresh() {
  await Promise.all([loadStats(), loadProjects(), loadLogs()]);
}
async function loadStats() {
  const s = await (await api("/stats")).json();
  const cards = [
    ["Requests", s.total_requests], ["Tokens", s.total_tokens],
    ["Cost (µ$)", s.total_cost_micro_usd], ["Avg latency", s.avg_latency_ms + " ms"]
  ];
  document.getElementById("statCards").innerHTML = cards.map(([k,v]) =>
    `<div class="card p-4"><div class="text-xs text-slate-400">${k}</div>
     <div class="text-2xl font-bold mt-1">${v}</div></div>`).join("");
}
async function loadProjects() {
  const list = await (await api("/projects")).json();
  if (!activeProject && list.length) activeProject = list[0].id;
  document.getElementById("projects").innerHTML = list.map(p =>
    `<div class="flex items-center justify-between rounded-lg px-3 py-2 ${p.id===activeProject?'bg-indigo-900/40 border border-indigo-700':'bg-slate-900/40'}">
       <button onclick="selectProject('${p.id}')" class="text-left">${p.name}<span class="text-xs text-slate-500 ml-2">${p.id.slice(0,8)}</span></button>
     </div>`).join("") || '<p class="text-slate-500">No projects yet.</p>';
  loadKeys();
}
window.selectProject = (id) => { activeProject = id; loadProjects(); };
document.getElementById("addProj").onclick = async () => {
  const name = document.getElementById("projName").value.trim();
  if (!name) return;
  await api("/projects", { method:"POST", body: JSON.stringify({name}) });
  document.getElementById("projName").value = ""; activeProject=null; loadProjects();
};
async function loadKeys() {
  if (!activeProject) { document.getElementById("keys").innerHTML=""; return; }
  const keys = await (await api(`/projects/${activeProject}/keys`)).json();
  document.getElementById("keys").innerHTML = keys.map(k =>
    `<div class="flex items-center justify-between rounded-lg px-3 py-2 bg-slate-900/40">
       <span><code>${k.prefix}…</code> <span class="text-slate-400">${k.name}</span>
       <span class="text-xs ${k.status==='active'?'text-emerald-400':'text-red-400'} ml-2">${k.status}</span></span>
       ${k.status==='active'?`<button onclick="revoke('${k.id}')" class="text-xs text-red-400 hover:text-red-300">Revoke</button>`:''}
     </div>`).join("") || '<p class="text-slate-500">No keys yet.</p>';
}
document.getElementById("addKey").onclick = async () => {
  if (!activeProject) return;
  const name = document.getElementById("keyName").value.trim() || "default";
  const res = await api(`/projects/${activeProject}/keys`, { method:"POST", body: JSON.stringify({name}) });
  const data = await res.json();
  const el = document.getElementById("newKey");
  el.textContent = "Copy now (shown once): " + data.api_key;
  el.classList.remove("hidden");
  document.getElementById("keyName").value = ""; loadKeys();
};
window.revoke = async (id) => { await api(`/keys/${id}/revoke`, {method:"POST"}); loadKeys(); };
async function loadLogs() {
  const { data } = await (await api("/logs?limit=25")).json();
  document.getElementById("logs").innerHTML = data.map(l =>
    `<tr class="border-b border-slate-800">
       <td class="py-2">${(l.created_at||'').slice(11,19)}</td>
       <td>${l.model}</td>
       <td class="${l.status==='success'?'text-emerald-400':'text-red-400'}">${l.status}</td>
       <td>${l.total_tokens}</td>
       <td>${l.latency_ms} ms</td>
       <td class="text-slate-500">${(l.request_id||'').slice(0,16)}</td>
     </tr>`).join("") || '<tr><td class="py-3 text-slate-500" colspan="6">No requests yet.</td></tr>';
}

if (token) { show("app"); refresh().catch(()=>logout()); } else { show("login"); }
setInterval(() => { if (token) refresh().catch(()=>{}); }, 5000);
</script>
</body>
</html>
"""
