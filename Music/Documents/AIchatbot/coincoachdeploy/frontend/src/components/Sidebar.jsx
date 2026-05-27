import React from 'react'
import OverviewTab from './tabs/OverviewTab'
import ExpensesTab from './tabs/ExpensesTab'
import HistoryTab  from './tabs/HistoryTab'
import PlanTab     from './tabs/PlanTab'
import styles from '../styles/Sidebar.module.css'

const TABS = [
  { id:'overview', label:'📊 Overview' },
  { id:'expenses', label:'🔀 Expenses' },
  { id:'history',  label:'📅 History'  },
  { id:'plan',     label:'🎯 Plan'     },
]

export default function Sidebar({ latestBudget, summary, activeTab, onTabChange }) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.tabs}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${styles.tab} ${activeTab===t.id ? styles.active : ''}`}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className={styles.body}>
        {activeTab==='overview' && <OverviewTab latestBudget={latestBudget} summary={summary} />}
        {activeTab==='expenses' && <ExpensesTab latestBudget={latestBudget} summary={summary} />}
        {activeTab==='history'  && <HistoryTab  summary={summary} />}
        {activeTab==='plan'     && <PlanTab     latestBudget={latestBudget} summary={summary} />}
      </div>
    </aside>
  )
}
