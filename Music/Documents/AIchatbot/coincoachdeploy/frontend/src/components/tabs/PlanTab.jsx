import React from 'react'
import { formatINR } from '../../utils/format'
import { todayStr } from '../../utils/dateUtils'
import styles from '../../styles/tabs/PlanTab.module.css'

const RULES=[
  {type:'warn',  title:'Pay yourself first',  text:'Set aside savings the moment money arrives.'},
  {type:'good',  title:'Track every rupee',   text:'What gets measured gets managed — you\'re doing it!'},
  {type:'good',  title:'1% improvement',      text:'Raise savings rate by 1% every 3 months.'},
  {type:'warn',  title:'Emergency fund',      text:'Target 3 months of expenses as liquid backup.'},
  {type:'danger',title:'No credit for wants', text:'Never finance lifestyle items on credit.'},
  {type:'good',  title:'Automate savings',    text:'Standing instruction on payday — not end of month.'},
]

export default function PlanTab({ latestBudget, summary }) {
  const mon    = summary?.thisMonth || {}
  const year   = summary?.thisYear  || {}
  const income = mon.totalIncome || 0
  const actual = mon.balance || 0
  const np=50,wp=30,sp=20
  const saves  = Math.round(income*sp/100)
  const shortfall = saves - actual

  return (
    <div className={styles.wrap}>
      {income > 0 ? (
        <div className={styles.planCard}>
          <div className={styles.cardHeader}>50 / 30 / 20 Plan <span className={styles.incLabel}>{formatINR(income)}/mo</span></div>
          <div className={styles.pills}>
            <div className={`${styles.pill} ${styles.needs}`}><span className={styles.pNum}>{np}%</span><span className={styles.pLbl}>Needs</span><span className={styles.pAmt}>{formatINR(Math.round(income*np/100))}</span></div>
            <div className={`${styles.pill} ${styles.wants}`}><span className={styles.pNum}>{wp}%</span><span className={styles.pLbl}>Wants</span><span className={styles.pAmt}>{formatINR(Math.round(income*wp/100))}</span></div>
            <div className={`${styles.pill} ${styles.saves}`}><span className={styles.pNum}>{sp}%</span><span className={styles.pLbl}>Saves</span><span className={styles.pAmt}>{formatINR(saves)}</span></div>
          </div>
          <div className={styles.actualRow}><span>Your actual balance this month</span><strong style={{color:actual>=0?'#c8f04e':'#f06060'}}>{formatINR(actual)}</strong></div>
          {actual<0?<div className={styles.alert}>⚠ Deficit of {formatINR(Math.abs(actual))} — reduce spending</div>
            :shortfall>0?<div className={styles.warn}>↑ Spend {formatINR(shortfall)} less to hit 20% savings</div>
            :<div className={styles.success}>✓ On track — great discipline!</div>}
          <div className={styles.rateLabel}>Savings rate: <strong style={{color:(mon.savingsRate||0)>=0?'#c8f04e':'#f06060'}}>{mon.savingsRate||0}%</strong> <span style={{color:'#5a5950'}}>(target 20%)</span></div>
          <div className={styles.rateTrack}><div className={styles.rateFill} style={{width:`${Math.min(100,Math.max(0,mon.savingsRate||0))}%`,background:(mon.savingsRate||0)>=20?'#4ecf8a':(mon.savingsRate||0)>=0?'#f5c842':'#f06060'}}/><div className={styles.rateTarget}/></div>
          <div className={styles.efund}>🏦 Emergency fund target: <strong>{formatINR(income*3)}</strong></div>
        </div>
      ) : (
        <div className={styles.empty}><div className={styles.emptyIcon}>🎯</div><div className={styles.emptyText}>Share any income or spending — your plan appears instantly.</div></div>
      )}

      {year.entryCount > 0 && (
        <div className={styles.yearCard}>
          <div className={styles.sLabel}>{todayStr().slice(0,4)} at a glance</div>
          <div className={styles.ypRow}><span>Received</span><span style={{color:'#4ecf8a'}}>{formatINR(year.totalIncome)}</span></div>
          <div className={styles.ypRow}><span>Spent</span><span style={{color:'#f06060'}}>{formatINR(year.totalExpenses)}</span></div>
          <div className={styles.ypRow}><span>Balance</span><span style={{color:(year.balance||0)>=0?'#c8f04e':'#f06060'}}>{formatINR(year.balance)}</span></div>
          <div className={styles.ypRow}><span>Savings rate</span><span style={{color:'#c8f04e'}}>{year.savingsRate||0}%</span></div>
        </div>
      )}

      {latestBudget?.motivation && <div className={styles.motivationBox}><span>✨</span><span>{latestBudget.motivation}</span></div>}

      <div className={styles.sLabel}>Saving Rules</div>
      <div className={styles.rules}>
        {RULES.map((r,i)=>(
          <div key={i} className={`${styles.rule} ${styles[r.type]}`}>
            <div className={styles.rTitle}>{r.title}</div>
            <div className={styles.rText}>{r.text}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
