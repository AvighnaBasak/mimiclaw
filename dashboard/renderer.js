'use strict'

// ── Clock ────────────────────────────────────────────────────────────────────
function tickClock() {
  const el = document.getElementById('clock')
  if (el) el.textContent = new Date().toLocaleTimeString()
}
setInterval(tickClock, 1000)
tickClock()

// ── Helpers ──────────────────────────────────────────────────────────────────
function statusPill(status) {
  const map = {
    completed:   ['pill-green',  'Completed'],
    pending:     ['pill-orange', 'Pending'],
    notified:    ['pill-orange', 'Notified'],
    in_progress: ['pill-blue',   'In Progress'],
    skipped:     ['pill-grey',   'Skipped'],
  }
  const [cls, label] = map[status] || ['pill-grey', status]
  return `<span class="pill ${cls}">${label}</span>`
}

function fmtDate(iso) {
  if (!iso) return '<span class="muted-text">No due date</span>'
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function daysUntil(iso) {
  if (!iso) return null
  const diff = Math.ceil((new Date(iso + 'T00:00:00') - new Date().setHours(0,0,0,0)) / 86400000)
  return diff
}

function daysPill(iso) {
  const d = daysUntil(iso)
  if (d === null) return ''
  if (d < 0)  return `<span class="days-pill" style="background:#FFEBEE;color:#c62828">${Math.abs(d)}d overdue</span>`
  if (d === 0) return `<span class="days-pill" style="background:#FFF3E0;color:#E65100">Today!</span>`
  if (d <= 3)  return `<span class="days-pill" style="background:var(--orange-light);color:var(--orange-dark)">${d}d left</span>`
  return `<span class="days-pill" style="background:#E8F5E9;color:#2E7D32">${d}d left</span>`
}

function driveLink(url) {
  if (!url) return '—'
  return `<a onclick="window.api.openUrl('${url}')">Open &#8599;</a>`
}

// ── Stats ────────────────────────────────────────────────────────────────────
async function loadStats() {
  const stats = await window.api.getStats()
  document.getElementById('stat-total').textContent     = stats.total
  document.getElementById('stat-completed').textContent = stats.completed
  document.getElementById('stat-pending').textContent   = stats.pending
  document.getElementById('stat-overdue').textContent   = stats.overdue
}

// ── Upcoming ─────────────────────────────────────────────────────────────────
async function loadPending() {
  const items = await window.api.getPending()
  const el = document.getElementById('upcoming-list')
  if (!items.length) {
    el.innerHTML = '<div class="empty-state">No pending assignments.</div>'
    return
  }
  const sorted = [...items].sort((a, b) => {
    if (!a.due_date) return 1
    if (!b.due_date) return -1
    return a.due_date.localeCompare(b.due_date)
  }).slice(0, 8)

  el.innerHTML = sorted.map(a => `
    <div class="upcoming-item">
      <div>
        <div class="upcoming-title">${esc(a.title)}</div>
        <div class="upcoming-course">${esc(a.course_name || '—')}</div>
      </div>
      <div class="upcoming-right">
        ${daysPill(a.due_date)}
        <div class="muted-text" style="margin-top:4px;font-size:0.75rem;">${fmtDate(a.due_date)}</div>
      </div>
    </div>
  `).join('')
}

// ── Reminders ────────────────────────────────────────────────────────────────
async function loadReminders() {
  const items = await window.api.getReminders()
  const el = document.getElementById('reminders-list')
  if (!items.length) {
    el.innerHTML = '<div class="empty-state">No reminders saved.</div>'
    return
  }
  el.innerHTML = items.slice(0, 10).map(r => `
    <div class="reminder-item">
      <div class="reminder-dot"></div>
      <div>
        <div class="reminder-text">${esc(r.text)}</div>
        <div class="reminder-date">${r.created_at ? new Date(r.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : ''}</div>
      </div>
    </div>
  `).join('')
}

// ── Completed ────────────────────────────────────────────────────────────────
async function loadCompleted() {
  const items = await window.api.getCompleted()
  const tbody = document.getElementById('completed-body')
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No completed assignments yet.</td></tr>'
    return
  }
  tbody.innerHTML = items.map(a => {
    const fileLinks = a.files && a.files.length
      ? a.files.map(f => `<a onclick="window.api.openUrl('${f.url}')">${esc(f.filename)}</a>`).join(', ')
      : driveLink(a.drive_folder_url)
    return `<tr>
      <td>${esc(a.title)}</td>
      <td>${esc(a.course_name || '—')}</td>
      <td>${fmtDate(a.due_date)}</td>
      <td>${fileLinks}</td>
    </tr>`
  }).join('')
}

// ── All Assignments ───────────────────────────────────────────────────────────
let allAssignments = []
let activeFilter = 'all'

async function loadAll() {
  document.getElementById('last-updated').textContent = 'Refreshing…'
  await Promise.all([loadStats(), loadPending(), loadReminders(), loadCompleted(), loadAllTable()])
  document.getElementById('last-updated').textContent =
    'Updated ' + new Date().toLocaleTimeString()
}

async function loadAllTable() {
  allAssignments = await window.api.getAssignments()
  renderAllTable()
}

function renderAllTable() {
  const tbody = document.getElementById('all-body')
  const filtered = activeFilter === 'all'
    ? allAssignments
    : allAssignments.filter(a => a.status === activeFilter ||
        (activeFilter === 'pending' && a.status === 'notified'))

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No assignments found.</td></tr>`
    return
  }
  tbody.innerHTML = filtered.map(a => `<tr>
    <td style="max-width:300px;">${esc(a.title)}</td>
    <td>${esc(a.course_name || '—')}</td>
    <td>${fmtDate(a.due_date)}</td>
    <td>${statusPill(a.status)}</td>
    <td>${driveLink(a.drive_folder_url)}</td>
  </tr>`).join('')
}

// ── Filter buttons ────────────────────────────────────────────────────────────
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'))
    btn.classList.add('active')
    activeFilter = btn.dataset.filter
    renderAllTable()
  })
})

// ── XSS-safe escape ───────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// ── Auto-refresh every 60s ────────────────────────────────────────────────────
loadAll()
setInterval(loadAll, 60000)
