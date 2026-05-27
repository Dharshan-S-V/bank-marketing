import React, { useState, useEffect } from 'react'
import { ICON_MAP } from '../../utils/constants'
import { formatINR } from '../../utils/format'
import styles from '../../styles/tabs/ExpensesTab.module.css'

export default function ExpensesTab({ summary }) {
  const [toggles, setToggles] = useState({})
  const mon      = summary?.thisMonth || {}
  const expenses = mon.expenses || {}
  const hasData  = Object.keys(expenses).length > 0

  useEffect(() => {
    const missing = {}
    Object.keys(expenses).forEach(k => { if (!(k in toggles)) missing[k] = true })
    if (Object.keys(missing).length) setToggles(p => ({ ...p, ...missing }))
  }, [JSON.stringify(Object.keys(expenses).sort())])

  const active = Object.entries(expenses).reduce((s,[k,v])=>s+(toggles[k]!==false?Number(v):0),0)
  const freed  = Object.entries(expenses).reduce((s,[k,v])=>s+(toggles[k]===false?Number(v):0),0)
  const inc    = mon.totalIncome || 0

  return (
    <div className={styles.wrap}>
      {!hasData ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>🔀</div>
          <div className={styles.emptyText}>Share your spending and toggles appear here instantly.</div>
        </div>
      ) : (
        <>
          <div className={styles.header}>
            <div className={styles.hItem}><div className={styles.hNum} style={{color:'#4ecf8a'}}>{formatINR(inc)}</div><div className={styles.hLbl}>Received</div></div>
            <div className={styles.hItem}><div className={styles.hNum} style={{color:'#f06060'}}>{formatINR(mon.totalExpenses||0)}</div><div className={styles.hLbl}>Spent</div></div>
            <div className={styles.hItem}><div className={styles.hNum} style={{color:(mon.balance||0)>=0?'#c8f04e':'#f06060'}}>{formatINR(mon.balance||0)}</div><div className={styles.hLbl}>{(mon.balance||0)>=0?'Balance':'Deficit'}</div></div>
          </div>
          <p className={styles.hint}>Toggle expenses to simulate savings.</p>
          <div className={styles.list}>
            {Object.entries(expenses).sort((a,b)=>Number(b[1])-Number(a[1])).map(([cat,val])=>{
              const pct = inc>0 ? Math.min(100,(Number(val)/inc*100)).toFixed(0) : 0
              return (
                <div key={cat} className={`${styles.row} ${toggles[cat]===false?styles.off:''}`}>
                  <div className={styles.left}>
                    <span className={styles.icon}>{ICON_MAP[cat]||'💸'}</span>
                    <div>
                      <div className={styles.name}>{cat}</div>
                      <div className={styles.amtRow}>
                        <span className={styles.amt}>{formatINR(Number(val))}</span>
                        {pct>0 && <span className={styles.pct} style={{color:pct>40?'#f06060':pct>20?'#f5c842':'#8a877e'}}>{pct}%</span>}
                      </div>
                      <div className={styles.miniBarTrack}><div className={styles.miniBarFill} style={{width:`${pct}%`,background:pct>40?'#f06060':pct>20?'#f5c842':'#4ecf8a'}}/></div>
                    </div>
                  </div>
                  <label className={styles.switch}>
                    <input type="checkbox" checked={toggles[cat]!==false} onChange={()=>setToggles(p=>({...p,[cat]:p[cat]===false}))}/>
                    <span className={styles.slider}/>
                  </label>
                </div>
              )
            })}
          </div>
          <div className={styles.summaryBox}>
            <div className={styles.sLabel}>Active Spend</div>
            <div className={styles.sNum}>{formatINR(active)}</div>
            <div className={styles.sHint}>{freed>0?`Free up ${formatINR(freed)}/mo by cutting toggled items`:'All expenses active'}</div>
          </div>
        </>
      )}
    </div>
  )
}
