import React from 'react'
import DonutChart from '../DonutChart'
import { formatINR, formatMonth } from '../../utils/format'
import { todayStr } from '../../utils/dateUtils'
import styles from '../../styles/tabs/OverviewTab.module.css'

function Stat({ label, value, color }) {
  return (
    <div className={styles.stat}>
      <div className={styles.statNum} style={{color}}>{formatINR(value)}</div>
      <div className={styles.statLbl}>{label}</div>
    </div>
  )
}

export default function OverviewTab({ latestBudget, summary }) {
  const today     = todayStr()
  const thisMonth = today.slice(0,7)
  const thisYear  = today.slice(0,4)

  const tod  = summary?.today      || {}
  const mon  = summary?.thisMonth  || {}
  const year = summary?.thisYear   || {}

  const donutExpenses = Object.keys(mon.expenses||{}).length > 0
    ? mon.expenses
    : (latestBudget?.entry?.expenses || {})

  const score = latestBudget?.health_score
  const scoreColor = !score ? '#c8f04e' :
    score>=80?'#4ecf8a': score>=60?'#c8f04e': score>=40?'#f5c842':'#f06060'

  return (
    <div className={styles.wrap}>
      {(tod.entryCount > 0 || tod.totalIncome > 0 || tod.totalExpenses > 0) && (
        <div className={styles.block}>
          <div className={styles.blockLabel}>Today · {today}</div>
          <div className={styles.statRow}>
            <Stat label="Received" value={tod.totalIncome||0}   color="#4ecf8a"/>
            <Stat label="Spent"    value={tod.totalExpenses||0} color="#f06060"/>
            <Stat label={(tod.balance||0)>=0?'Saved':'Deficit'} value={tod.balance||0}
              color={(tod.balance||0)>=0?'#c8f04e':'#f06060'}/>
          </div>
        </div>
      )}

      {(mon.entryCount > 0 || mon.totalIncome > 0) && (
        <div className={styles.block}>
          <div className={styles.blockLabel}>{formatMonth(thisMonth)}</div>
          <div className={styles.statRow}>
            <Stat label="Received" value={mon.totalIncome||0}   color="#4ecf8a"/>
            <Stat label="Spent"    value={mon.totalExpenses||0} color="#f06060"/>
            <Stat label={(mon.balance||0)>=0?'Saved':'Deficit'} value={mon.balance||0}
              color={(mon.balance||0)>=0?'#c8f04e':'#f06060'}/>
          </div>
          <div className={styles.subInfo}>
            {mon.entryCount||0} day{mon.entryCount!==1?'s':''} logged
            <span style={{color:(mon.savingsRate||0)>=0?'#c8f04e':'#f06060'}}>
              {' '}· {mon.savingsRate||0}% savings rate
            </span>
          </div>
        </div>
      )}

      {year.entryCount > 0 && (
        <div className={styles.yearStrip}>
          <span className={styles.yearLabel}>{thisYear}</span>
          <span style={{color:'#4ecf8a'}}>{formatINR(year.totalIncome)}</span>
          <span className={styles.arr}>→</span>
          <span style={{color:'#f06060'}}>{formatINR(year.totalExpenses)}</span>
          <span className={styles.arr}>→</span>
          <span style={{color:(year.balance||0)>=0?'#c8f04e':'#f06060'}}>{formatINR(year.balance)}</span>
        </div>
      )}

      {Object.keys(donutExpenses).length > 0 && (
        <>
          <div className={styles.sectionLabel}>Spending breakdown</div>
          <DonutChart expenses={donutExpenses}/>
        </>
      )}

      {latestBudget && (
        <>
          <div className={styles.divider}/>
          <div className={styles.sectionLabel}>Financial Health</div>
          <div className={styles.scoreCard}>
            <div className={styles.scoreRow}>
              <div>
                <div className={styles.scoreBig} style={{color:scoreColor}}>{score}</div>
                <div className={styles.scoreLbl}>Score / 100</div>
              </div>
              <div className={styles.gradeTag}>{latestBudget.grade}</div>
            </div>
            <div className={styles.barTrack}>
              <div className={styles.barFill} style={{width:`${score}%`,background:scoreColor}}/>
            </div>
          </div>
        </>
      )}

      {latestBudget?.motivation && (
        <div className={styles.motivationBox}>
          <span>✨</span><span>{latestBudget.motivation}</span>
        </div>
      )}

      {latestBudget?.tips?.length > 0 && (
        <>
          <div className={styles.sectionLabel}>Tips</div>
          <div className={styles.tipsList}>
            {latestBudget.tips.map((t,i)=>(
              <div key={i} className={`${styles.tipItem} ${styles[t.type]}`}>
                <div className={styles.tipTitle}>{t.title}</div>
                <div>{t.text}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {!summary && !latestBudget && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>💬</div>
          <div className={styles.emptyText}>Tell me what you received or spent today — overview fills automatically.</div>
        </div>
      )}
    </div>
  )
}
