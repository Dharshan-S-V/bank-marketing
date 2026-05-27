/**
 * Ledger — source of truth for all financial data.
 *
 * Data shape:
 * {
 *   userProfile: { name, createdAt },
 *   entries: [
 *     {
 *       id: "2025-05-23",          // date is the unique key — ONE entry per date
 *       date: "2025-05-23",
 *       income: 500,
 *       expenses: { "Travelling": 300, "Eating outside": 200 },
 *       note: "pocket money, petrol, food",
 *       updatedAt: "ISO string"
 *     }
 *   ]
 * }
 *
 * Rule: ONE entry per calendar date. Corrections REPLACE, new days MERGE.
 */

const KEY = 'coincoach_ledger_v4'

export function loadLedger() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { userProfile: null, entries: [] }
}

export function saveLedger(ledger) {
  try { localStorage.setItem(KEY, JSON.stringify(ledger)) } catch {}
}

export function clearLedger() { localStorage.removeItem(KEY) }

export function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export function getWeekKey(dateStr) {
  // Returns "YYYY-Www" — ISO week
  const d = new Date(dateStr + 'T00:00:00')
  const jan4 = new Date(d.getFullYear(), 0, 4)
  const dayOfYear = Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 86400000)
  const week = Math.ceil((dayOfYear + jan4.getDay()) / 7)
  return `${d.getFullYear()}-W${String(week).padStart(2,'0')}`
}

export function getMonthKey(dateStr) { return dateStr.slice(0, 7) }
export function getYearKey(dateStr)  { return dateStr.slice(0, 4) }

export function setUserProfile(ledger, profile) {
  const updated = {
    ...ledger,
    userProfile: { ...profile, createdAt: ledger.userProfile?.createdAt || new Date().toISOString() }
  }
  saveLedger(updated)
  return updated
}

/**
 * NEW ENTRY — adds to the existing entry for that date (accumulate).
 * e.g. morning: petrol ₹200, evening: food ₹100 → same day, merged.
 */
export function addEntry(ledger, newEntry) {
  const date = newEntry.date || todayStr()
  const existing = ledger.entries.find(e => e.date === date)

  let entries
  if (existing) {
    // Same day: ADD new amounts on top of existing
    const merged = {
      ...existing,
      income: (existing.income || 0) + (newEntry.income || 0),
      expenses: { ...existing.expenses },
      note: [existing.note, newEntry.note].filter(Boolean).join(' | '),
      updatedAt: new Date().toISOString(),
    }
    for (const [cat, amt] of Object.entries(newEntry.expenses || {})) {
      merged.expenses[cat] = (merged.expenses[cat] || 0) + amt
    }
    entries = ledger.entries.map(e => e.date === date ? merged : e)
  } else {
    // New day: create fresh entry
    const entry = {
      id:        date,
      date,
      income:    newEntry.income || 0,
      expenses:  { ...(newEntry.expenses || {}) },
      note:      newEntry.note || '',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    entries = [...ledger.entries, entry].sort((a,b) => a.date.localeCompare(b.date))
  }

  const updated = { ...ledger, entries }
  saveLedger(updated)
  return updated
}

/**
 * CORRECTION — completely REPLACES the entry for that date.
 * Used when user says "I made a mistake" or corrects a value.
 */
export function correctEntry(ledger, correctedEntry) {
  const date = correctedEntry.date || todayStr()
  const replacement = {
    id:        date,
    date,
    income:    correctedEntry.income || 0,
    expenses:  { ...(correctedEntry.expenses || {}) },
    note:      correctedEntry.note || '',
    createdAt: ledger.entries.find(e => e.date === date)?.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    corrected: true,
  }

  let entries
  if (ledger.entries.find(e => e.date === date)) {
    entries = ledger.entries.map(e => e.date === date ? replacement : e)
  } else {
    entries = [...ledger.entries, replacement].sort((a,b) => a.date.localeCompare(b.date))
  }

  const updated = { ...ledger, entries }
  saveLedger(updated)
  return updated
}

// ── Aggregation ───────────────────────────────────────────────────────────────

export function aggregateEntries(entries) {
  let totalIncome = 0
  const expenses  = {}
  for (const e of entries) {
    totalIncome += (e.income || 0)
    for (const [cat, amt] of Object.entries(e.expenses || {})) {
      expenses[cat] = (expenses[cat] || 0) + amt
    }
  }
  const totalExpenses = Object.values(expenses).reduce((a, b) => a + b, 0)
  const balance       = totalIncome - totalExpenses
  const savingsRate   = totalIncome > 0 ? +((balance / totalIncome) * 100).toFixed(1) : 0
  return { totalIncome, expenses, totalExpenses, balance, savingsRate, entryCount: entries.length }
}

export function aggregateByDay(entries, dateStr) {
  return aggregateEntries(entries.filter(e => e.date === dateStr))
}

export function aggregateByWeek(entries, weekKey) {
  return aggregateEntries(entries.filter(e => getWeekKey(e.date) === weekKey))
}

export function aggregateByMonth(entries, monthKey) {
  return aggregateEntries(entries.filter(e => getMonthKey(e.date) === monthKey))
}

export function aggregateByYear(entries, year) {
  return aggregateEntries(entries.filter(e => getYearKey(e.date) === String(year)))
}

export function getWeeklyBreakdown(entries, monthKey) {
  // Group entries in a given month by week
  const inMonth = entries.filter(e => getMonthKey(e.date) === monthKey)
  const weeks = {}
  for (const e of inMonth) {
    const wk = getWeekKey(e.date)
    if (!weeks[wk]) weeks[wk] = []
    weeks[wk].push(e)
  }
  return Object.entries(weeks)
    .sort(([a],[b]) => a.localeCompare(b))
    .map(([week, ents]) => ({ week, ...aggregateEntries(ents) }))
}

export function getMonthlyBreakdown(entries) {
  const months = {}
  for (const e of entries) {
    const mk = getMonthKey(e.date)
    if (!months[mk]) months[mk] = []
    months[mk].push(e)
  }
  return Object.entries(months)
    .sort(([a],[b]) => a.localeCompare(b))
    .map(([month, ents]) => ({ month, ...aggregateEntries(ents) }))
}

export function getLedgerSummaryForAI(ledger) {
  if (!ledger.entries.length) return null
  const today     = todayStr()
  const thisMonth = today.slice(0, 7)
  const thisYear  = today.slice(0, 4)
  const todayData = aggregateByDay(ledger.entries, today)
  const monthData = aggregateByMonth(ledger.entries, thisMonth)
  const yearData  = aggregateByYear(ledger.entries, thisYear)
  return {
    userProfile:   ledger.userProfile,
    today:         { date: today, ...todayData },
    thisMonth:     { key: thisMonth, ...monthData },
    thisYear:      { key: thisYear, ...yearData },
    recentEntries: ledger.entries.slice(-5),
    totalEntries:  ledger.entries.length,
    trackingSince: ledger.entries[0]?.date,
  }
}
