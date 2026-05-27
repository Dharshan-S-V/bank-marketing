export function formatBubble(text) {
  const lines = text.split('\n')
  let out = '', inList = false
  for (let line of lines) {
    line = line.trim()
    if (!line) {
      if (inList) { out += '</ul>'; inList = false }
      out += '<br/>'
      continue
    }
    if (/^\*\*(.+?)\*\*:?$/.test(line)) {
      if (inList) { out += '</ul>'; inList = false }
      const label = line.replace(/\*\*/g,'').replace(/:$/,'')
      out += `<span class="b-section">${label}</span>`
      continue
    }
    if (/^[•\-\*]/.test(line)) {
      const content = line.replace(/^[•\-\*]\s*/,'').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')
      if (!inList) { out += '<ul>'; inList = true }
      out += `<li>${content}</li>`
      continue
    }
    if (inList) { out += '</ul>'; inList = false }
    out += line.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>') + '<br/>'
  }
  if (inList) out += '</ul>'
  return out.replace(/<br\/>$/,'')
}

export function formatINR(n) {
  const num = Number(n || 0)
  const abs = Math.abs(num)
  return (num < 0 ? '-' : '') + '₹' + abs.toLocaleString('en-IN')
}

export function parseBudgetJSON(text) {
  const match = text.match(/<budget_json>([\s\S]*?)<\/budget_json>/)
  if (!match) return null
  try { return JSON.parse(match[1].trim()) } catch { return null }
}

export function stripBudgetJSON(text) {
  return text.replace(/<budget_json>[\s\S]*?<\/budget_json>/,'').trim()
}

export function formatDate(dateStr) {
  try {
    const d = new Date(String(dateStr).slice(0,10) + 'T00:00:00')
    return d.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})
  } catch { return String(dateStr).slice(0,10) }
}

export function formatMonth(monthKey) {
  const [y,m] = String(monthKey).split('-')
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[parseInt(m)-1]} ${y}`
}
