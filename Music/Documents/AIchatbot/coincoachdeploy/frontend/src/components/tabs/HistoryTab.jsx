import React, { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { formatINR, formatDate, formatMonth } from '../../utils/format'
import { getWeekKey } from '../../utils/dateUtils'
import styles from '../../styles/tabs/HistoryTab.module.css'

function BalancePill({ value }) {
  const neg = value < 0
  return <span className={styles.balPill} style={{color:neg?'#f06060':'#4ecf8a',background:neg?'rgba(240,96,96,.12)':'rgba(78,207,138,.12)'}}>{neg?'▼':'▲'} {formatINR(value)}</span>
}

export default function HistoryTab({ summary }) {
  const [view, setView]       = useState('daily')
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(false)
  const [year, setYear]       = useState(new Date().getFullYear())

  const thisMonth = new Date().toISOString().slice(0,7)

  useEffect(() => {
    loadEntries()
  }, [view, year])

  async function loadEntries() {
    setLoading(true)
    try {
      let params = {}
      if (view === 'daily' || view === 'weekly') params = { month: thisMonth }
      else if (view === 'monthly') params = { year }
      else if (view === 'yearly') params = { year, limit: 400 }
      const res = await api.getEntries(params)
      setEntries(res.entries || [])
    } catch {}
    setLoading(false)
  }

  // Aggregate entries into weekly buckets
  function groupByWeek(ents) {
    const weeks = {}
    for (const e of ents) {
      const wk = getWeekKey(e.date)
      if (!weeks[wk]) weeks[wk] = { week:wk, entries:[], income:0, spent:0 }
      weeks[wk].entries.push(e)
      weeks[wk].income += Number(e.income||0)
      const s = Object.values(e.expenses||{}).reduce((a,b)=>a+Number(b),0)
      weeks[wk].spent += s
    }
    return Object.values(weeks).sort((a,b)=>b.week.localeCompare(a.week)).map(w=>({...w,balance:w.income-w.spent}))
  }

  // Aggregate entries into monthly buckets
  function groupByMonth(ents) {
    const months = {}
    for (const e of ents) {
      const mk = e.date.slice(0,7)
      if (!months[mk]) months[mk] = { month:mk, entries:[], income:0, expenses:{}, spent:0 }
      months[mk].entries.push(e)
      months[mk].income += Number(e.income||0)
      for (const [cat,amt] of Object.entries(e.expenses||{})) {
        months[mk].expenses[cat] = (months[mk].expenses[cat]||0) + Number(amt)
        months[mk].spent += Number(amt)
      }
    }
    return Object.values(months).sort((a,b)=>b.month.localeCompare(a.month)).map(m=>({...m,balance:m.income-m.spent,savingsRate:m.income>0?+((m.income-m.spent)/m.income*100).toFixed(1):0}))
  }

  if (!summary && !entries.length && !loading) return (
    <div className={styles.empty}>
      <div className={styles.emptyIcon}>📅</div>
      <div className={styles.emptyText}>No entries yet. Start chatting to log spending — it records per date automatically.</div>
    </div>
  )

  return (
    <div className={styles.wrap}>
      <div className={styles.viewToggle}>
        {[{id:'daily',l:'📋 Daily'},{id:'weekly',l:'📅 Weekly'},{id:'monthly',l:'🗓 Monthly'},{id:'yearly',l:'📆 Yearly'}].map(v=>(
          <button key={v.id} className={`${styles.vBtn} ${view===v.id?styles.vActive:''}`} onClick={()=>setView(v.id)}>{v.l}</button>
        ))}
      </div>

      {loading && <div className={styles.loading}>Loading…</div>}

      {/* DAILY */}
      {view==='daily' && !loading && (
        <div className={styles.list}>
          {entries.length===0 && <div className={styles.noData}>No entries this month.</div>}
          {entries.map(e=>{
            const spent = Object.values(e.expenses||{}).reduce((a,b)=>a+Number(b),0)
            const bal   = Number(e.income||0) - spent
            return (
              <div key={e.id} className={`${styles.card} ${e.corrected?styles.corrected:''}`}>
                <div className={styles.cardTop}>
                  <div>
                    <div className={styles.cardDate}>{formatDate(e.date)}</div>
                    {e.date===new Date().toISOString().slice(0,10) && <span className={styles.badge} style={{background:'rgba(200,240,78,.12)',color:'#c8f04e'}}>Today</span>}
                    {e.corrected && <span className={styles.badge} style={{background:'rgba(245,200,66,.1)',color:'#f5c842'}}>Corrected</span>}
                  </div>
                  <BalancePill value={bal}/>
                </div>
                {e.note && <div className={styles.note}>{e.note}</div>}
                <div className={styles.cardStats}>
                  {Number(e.income)>0 && <div className={styles.statRow}><span>Received</span><span style={{color:'#4ecf8a'}}>{formatINR(e.income)}</span></div>}
                  {Object.entries(e.expenses||{}).map(([cat,amt])=>(
                    <div key={cat} className={styles.statRow}><span>{cat}</span><span style={{color:'#f06060'}}>{formatINR(Number(amt))}</span></div>
                  ))}
                  <div className={styles.divider}/>
                  <div className={styles.statRow}><span>Balance</span><span style={{color:bal>=0?'#c8f04e':'#f06060'}}>{formatINR(bal)}</span></div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* WEEKLY */}
      {view==='weekly' && !loading && (
        <div className={styles.list}>
          <div className={styles.periodLabel}>{formatMonth(thisMonth)} — by week</div>
          {groupByWeek(entries).map((w,i,arr)=>(
            <div key={w.week} className={styles.card}>
              <div className={styles.cardTop}>
                <div><div className={styles.cardDate}>Week {arr.length-i} · {w.week}</div><div className={styles.entryCount}>{w.entries.length} day{w.entries.length!==1?'s':''}</div></div>
                <BalancePill value={w.balance}/>
              </div>
              <div className={styles.cardStats}>
                <div className={styles.statRow}><span>Received</span><span style={{color:'#4ecf8a'}}>{formatINR(w.income)}</span></div>
                <div className={styles.statRow}><span>Spent</span><span style={{color:'#f06060'}}>{formatINR(w.spent)}</span></div>
                <div className={styles.divider}/>
                <div className={styles.statRow}><span>Balance</span><span style={{color:w.balance>=0?'#c8f04e':'#f06060'}}>{formatINR(w.balance)}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MONTHLY */}
      {view==='monthly' && !loading && (
        <div className={styles.list}>
          {groupByMonth(entries).map(m=>(
            <div key={m.month} className={styles.card}>
              <div className={styles.cardTop}>
                <div><div className={styles.cardDate}>{formatMonth(m.month)}</div><div className={styles.entryCount}>{m.entries.length} days · {m.savingsRate}% saved</div></div>
                <BalancePill value={m.balance}/>
              </div>
              <div className={styles.cardStats}>
                <div className={styles.statRow}><span>Received</span><span style={{color:'#4ecf8a'}}>{formatINR(m.income)}</span></div>
                <div className={styles.statRow}><span>Spent</span><span style={{color:'#f06060'}}>{formatINR(m.spent)}</span></div>
                <div className={styles.divider}/>
                <div className={styles.statRow}><span>Balance</span><span style={{color:m.balance>=0?'#c8f04e':'#f06060'}}>{formatINR(m.balance)}</span></div>
              </div>
              <div className={styles.expBreak}>
                {Object.entries(m.expenses).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([cat,amt])=>(
                  <div key={cat} className={styles.expRow}><span>{cat}</span><span style={{color:'#f06060'}}>{formatINR(amt)}</span></div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* YEARLY */}
      {view==='yearly' && !loading && summary?.thisYear && (
        <div className={styles.list}>
          <div className={styles.card}>
            <div className={styles.cardTop}>
              <div><div className={styles.cardDate}>Year {new Date().getFullYear()}</div><div className={styles.entryCount}>{summary.thisYear.entryCount} days logged</div></div>
              <BalancePill value={summary.thisYear.balance||0}/>
            </div>
            <div className={styles.cardStats}>
              <div className={styles.statRow}><span>Total received</span><span style={{color:'#4ecf8a'}}>{formatINR(summary.thisYear.totalIncome)}</span></div>
              <div className={styles.statRow}><span>Total spent</span><span style={{color:'#f06060'}}>{formatINR(summary.thisYear.totalExpenses)}</span></div>
              <div className={styles.divider}/>
              <div className={styles.statRow}><span>Total saved</span><span style={{color:(summary.thisYear.balance||0)>=0?'#c8f04e':'#f06060'}}>{formatINR(summary.thisYear.balance)}</span></div>
              <div className={styles.statRow}><span>Annual savings rate</span><span style={{color:'#c8f04e'}}>{summary.thisYear.savingsRate||0}%</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
