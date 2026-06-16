import { useEffect, useState, useCallback } from 'react'

const API = '' // same origin as FastAPI

async function getJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}
async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  return r.json()
}

const fmtTime = (iso) => {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) }
  catch { return iso }
}

const scoreColor = (s) =>
  s >= 8 ? 'text-emerald-400 bg-emerald-500/10 ring-emerald-500/30'
  : s >= 6 ? 'text-amber-400 bg-amber-500/10 ring-amber-500/30'
  : 'text-sky-400 bg-sky-500/10 ring-sky-500/30'

/* ── Small UI primitives ─────────────────────────────── */
function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm ${className}`}>
      {children}
    </div>
  )
}

function Stat({ label, value, sub, accent = 'from-indigo-500/20 to-purple-500/10' }) {
  return (
    <Card className="p-5 relative overflow-hidden">
      <div className={`absolute inset-0 bg-gradient-to-br ${accent} opacity-60 pointer-events-none`} />
      <div className="relative">
        <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
        <div className="mt-2 text-3xl font-semibold text-white">{value}</div>
        {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
      </div>
    </Card>
  )
}

function Pill({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-500/15 text-slate-300 ring-slate-400/20',
    green: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
    amber: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
    red: 'bg-rose-500/15 text-rose-300 ring-rose-400/30',
  }
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ring-1 ${tones[tone]}`}>{children}</span>
}

/* ── Opportunity card ────────────────────────────────── */
function OppCard({ o }) {
  const score = Number(o.total_score || 0)
  const ai = o.ai_analysis || {}
  const emoji = score >= 8 ? '🔥' : score >= 6 ? '⭐' : '📌'
  return (
    <Card className="p-5 hover:border-white/20 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-white leading-snug">{o.title || 'Untitled tender'}</h3>
        <span className={`shrink-0 rounded-lg px-2.5 py-1 text-sm font-bold ring-1 ${scoreColor(score)}`}>
          {emoji} {score}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <Field label="Value" value={o.value} />
        <Field label="Sector" value={o.sector} />
        <Field label="Dept" value={o.department} />
        <Field label="Location" value={o.location} />
        <Field label="Deadline" value={o.deadline} />
        <Field label="Source" value={o.source} />
      </div>
      {ai.key_insight && (
        <p className="mt-3 text-sm text-slate-300 italic border-l-2 border-indigo-400/40 pl-3">
          💡 {ai.key_insight}
        </p>
      )}
      {ai.action_required && (
        <p className="mt-2 text-sm text-emerald-300/90">✅ {ai.action_required}</p>
      )}
      {o.url && o.url !== '#' && (
        <a href={o.url} target="_blank" rel="noreferrer"
           className="mt-3 inline-block text-xs text-sky-400 hover:text-sky-300">
          View full tender →
        </a>
      )}
    </Card>
  )
}
function Field({ label, value }) {
  if (!value) return null
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-slate-200 truncate">{value}</div>
    </div>
  )
}

function Empty({ children }) {
  return <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-slate-500 text-sm">{children}</div>
}

/* ── Tabs content ────────────────────────────────────── */
function Overview({ data }) {
  const opps = data?.tenders?.top_opportunities || []
  const insights = data?.tenders?.sector_insights || ''
  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Top Opportunities</h2>
        {opps.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {opps.map((o, i) => <OppCard key={i} o={o} />)}
          </div>
        ) : <Empty>No opportunities yet — click <b className="text-slate-300">Run scan</b> to generate.</Empty>}
      </section>
      {insights && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Sector Intelligence</h2>
          <Card className="p-5">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-300">{insights}</pre>
          </Card>
        </section>
      )}
    </div>
  )
}

function Tenders() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)

  const loadRecent = useCallback(async () => {
    setLoading(true)
    try { const d = await getJSON(`${API}/api/tenders?limit=30`); setItems(d.tenders || []) }
    catch { setItems([]) } finally { setLoading(false) }
  }, [])
  useEffect(() => { loadRecent() }, [loadRecent])

  const search = async (e) => {
    e.preventDefault()
    if (!q.trim()) return loadRecent()
    setLoading(true)
    try {
      const d = await postJSON(`${API}/api/tenders/search`, { query: q, limit: 30 })
      setItems((d.results || []).map(r => ({ ...r })))
    } catch { setItems([]) } finally { setLoading(false) }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={search} className="flex gap-2">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="Semantic search… e.g. solar power Telangana"
          className="flex-1 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-indigo-400/50" />
        <button className="rounded-xl bg-indigo-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-400">Search</button>
      </form>
      {loading ? <Empty>Loading…</Empty> : items.length ? (
        <div className="grid gap-3">
          {items.map((t, i) => {
            const m = t.metadata || t
            return (
              <Card key={i} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="font-medium text-white">{m.title || '—'}</div>
                  {t.relevance_score != null && <Pill tone="green">{t.relevance_score}% match</Pill>}
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                  {m.sector && <span>🏷 {m.sector}</span>}
                  {m.value && <span>💰 {m.value}</span>}
                  {m.location && <span>📍 {m.location}</span>}
                  {m.deadline && <span>⏰ {m.deadline}</span>}
                  {m.source && <span>📡 {m.source}</span>}
                </div>
              </Card>
            )
          })}
        </div>
      ) : <Empty>No tenders found.</Empty>}
    </div>
  )
}

function KeyVals({ obj }) {
  const entries = Object.entries(obj || {}).filter(([, v]) => typeof v !== 'object')
  if (!entries.length) return <Empty>No data yet.</Empty>
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {entries.map(([k, v]) => (
        <Stat key={k} label={k.replace(/_/g, ' ')}
          value={typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : String(v)}
          accent="from-slate-500/10 to-slate-400/5" />
      ))}
    </div>
  )
}

function ListSection({ title, items, render }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">{title}</h2>
      {items?.length ? <div className="grid gap-3">{items.map(render)}</div> : <Empty>No {title.toLowerCase()} yet.</Empty>}
    </section>
  )
}

function Market({ data }) {
  const w = data?.market?.early_warnings || []
  const b = data?.market?.bulk_deals || []
  return (
    <div className="space-y-6">
      <ListSection title="Early Warnings" items={w} render={(x, i) => (
        <Card key={i} className="p-4 text-sm text-slate-200">
          <pre className="whitespace-pre-wrap font-sans">{typeof x === 'string' ? x : JSON.stringify(x, null, 2)}</pre>
        </Card>
      )} />
      <ListSection title="Bulk Deals" items={b} render={(x, i) => (
        <Card key={i} className="p-4 text-sm text-slate-300">
          {x.company || x.symbol || JSON.stringify(x)}
        </Card>
      )} />
    </div>
  )
}

function Stocks({ data }) {
  const s = data?.stocks?.signals || []
  const pf = data?.stocks?.portfolio || {}
  const open = data?.stocks?.open_trades || []
  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Portfolio</h2>
        <KeyVals obj={pf} />
      </section>
      <ListSection title="Signals" items={s} render={(x, i) => (
        <Card key={i} className="p-4 flex items-center justify-between text-sm">
          <span className="font-medium text-white">{x.symbol || x.company || '—'}</span>
          <Pill tone={x.action === 'BUY' ? 'green' : x.action === 'SELL' ? 'red' : 'slate'}>
            {x.action || 'WATCH'} {x.strength != null ? `· ${x.strength}` : ''}
          </Pill>
        </Card>
      )} />
      <ListSection title="Open Trades" items={open} render={(x, i) => (
        <Card key={i} className="p-4 text-sm text-slate-300">{JSON.stringify(x)}</Card>
      )} />
    </div>
  )
}

function Revenue({ data }) {
  const r = data?.revenue || {}
  const subs = r.subscribers || []
  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Revenue Metrics</h2>
        <KeyVals obj={r} />
      </section>
      <ListSection title="Recent Subscribers" items={subs} render={(s, i) => (
        <Card key={i} className="p-4 flex items-center justify-between text-sm">
          <span className="text-white">{s.name || '—'}</span>
          <Pill tone="green">{s.tier || 'basic'}</Pill>
        </Card>
      )} />
    </div>
  )
}

/* ── Main App ────────────────────────────────────────── */
const TABS = ['Overview', 'Tenders', 'Market', 'Stocks', 'Revenue']

export default function App() {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('Overview')
  const [err, setErr] = useState('')
  const [running, setRunning] = useState(false)
  const [step, setStep] = useState('')

  const load = useCallback(async () => {
    try { const d = await getJSON(`${API}/api/overview`); setData(d); setErr(d.error || '') }
    catch (e) { setErr('Cannot reach API — is the server running?') }
  }, [])

  useEffect(() => { load() }, [load])

  // poll pipeline status while running
  useEffect(() => {
    if (!running) return
    const id = setInterval(async () => {
      try {
        const s = await getJSON(`${API}/api/pipeline/status`)
        setStep(s.current_step || '')
        if (!s.is_running) { setRunning(false); setStep(''); load() }
      } catch {}
    }, 2500)
    return () => clearInterval(id)
  }, [running, load])

  const runScan = async (mode = 'scout') => {
    setRunning(true); setStep('Starting…')
    try { await postJSON(`${API}/api/pipeline/run?mode=${mode}`, {}) }
    catch { setRunning(false); setStep('') }
  }

  const total = data?.tenders?.total_tracked ?? '—'
  const oppCount = data?.tenders?.top_opportunities?.length ?? 0
  const warnCount = data?.market?.early_warnings?.length ?? 0
  const sigCount = data?.stocks?.signals?.length ?? 0
  const lastRun = data?.pipeline?.last_run

  return (
    <div className="min-h-full text-slate-200">
      {/* glow background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-32 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="absolute top-20 right-0 h-96 w-96 rounded-full bg-fuchsia-600/10 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-5 py-8">
        {/* Header */}
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <span className="bg-gradient-to-r from-indigo-400 to-fuchsia-400 bg-clip-text text-transparent">
                Opportunity Scout
              </span>
              <span className="text-base">🇮🇳</span>
            </h1>
            <p className="text-sm text-slate-400">India Infrastructure Intelligence · Live Dashboard</p>
          </div>
          <div className="flex items-center gap-3">
            {running
              ? <Pill tone="amber"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" /> {step || 'Running…'}</Pill>
              : <Pill tone="green"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Idle</Pill>}
            <button onClick={() => runScan('scout')} disabled={running}
              className="rounded-xl bg-gradient-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:opacity-90 disabled:opacity-50">
              {running ? 'Scanning…' : '⚡ Run scan'}
            </button>
          </div>
        </header>

        {err && (
          <div className="mt-5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            {err}
          </div>
        )}

        {/* Stat row */}
        <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Tenders tracked" value={total} sub="in vector memory" accent="from-indigo-500/20 to-purple-500/10" />
          <Stat label="Top opportunities" value={oppCount} sub="last scan" accent="from-emerald-500/20 to-teal-500/10" />
          <Stat label="Market warnings" value={warnCount} sub="early signals" accent="from-amber-500/20 to-orange-500/10" />
          <Stat label="Stock signals" value={sigCount} sub="from tenders" accent="from-sky-500/20 to-cyan-500/10" />
        </div>

        {/* Tabs */}
        <nav className="mt-8 flex gap-1 rounded-xl border border-white/10 bg-white/[0.02] p-1">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition ${
                tab === t ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-slate-200'}`}>
              {t}
            </button>
          ))}
        </nav>

        <main className="mt-6 pb-12">
          {tab === 'Overview' && <Overview data={data} />}
          {tab === 'Tenders' && <Tenders />}
          {tab === 'Market' && <Market data={data} />}
          {tab === 'Stocks' && <Stocks data={data} />}
          {tab === 'Revenue' && <Revenue data={data} />}
        </main>

        <footer className="border-t border-white/10 pt-4 text-xs text-slate-500 flex justify-between">
          <span>Last scan: {fmtTime(lastRun)}</span>
          <span>Powered by NVIDIA NIM · FastAPI · React + Tailwind</span>
        </footer>
      </div>
    </div>
  )
}
