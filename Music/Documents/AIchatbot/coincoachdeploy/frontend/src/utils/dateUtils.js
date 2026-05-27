export function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export function getMonthKey(dateStr) { return String(dateStr).slice(0, 7) }
export function getYearKey(dateStr)  { return String(dateStr).slice(0, 4) }

export function getWeekKey(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  const jan4 = new Date(d.getFullYear(), 0, 4)
  const dayOfYear = Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 86400000)
  const week = Math.ceil((dayOfYear + jan4.getDay()) / 7)
  return `${d.getFullYear()}-W${String(week).padStart(2,'0')}`
}

export function formatDate(dateStr) {
  try {
    const d = new Date(String(dateStr).slice(0,10) + 'T00:00:00')
    return d.toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })
  } catch { return String(dateStr).slice(0,10) }
}

export function formatMonth(monthKey) {
  const [y, m] = String(monthKey).split('-')
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[parseInt(m)-1]} ${y}`
}
