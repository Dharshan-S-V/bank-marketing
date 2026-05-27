import React from 'react'
import { RATE_LIMIT } from '../utils/constants'
import styles from '../styles/Header.module.css'

export default function Header({ callCount, user, onReset, onLogout }) {
  const pct   = (callCount / RATE_LIMIT) * 100
  const color = pct > 80 ? 'var(--danger)' : pct > 55 ? 'var(--warn)' : 'var(--accent)'

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <div className={styles.logo}>
          <span className={styles.logoMark}>◈</span>
          Coin<em>Coach</em>
        </div>
        {user && (
          <div className={styles.userChip}>
            <span className={styles.chipDot}/>
            {user.name}
          </div>
        )}
      </div>

      <div className={styles.center}>
        <div className={styles.ratePill}>
          <div className={styles.rateTrack}>
            <div className={styles.rateFill} style={{ width:`${pct}%`, background:color }}/>
          </div>
          <span className={styles.rateText} style={{ color }}>
            {RATE_LIMIT - callCount} calls left
          </span>
        </div>
      </div>

      <div className={styles.right}>
        <button className={styles.iconBtn} onClick={onReset} title="New chat">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
        </button>
        <button className={styles.logoutBtn} onClick={onLogout}>
          Sign out
        </button>
        <div className={styles.liveIndicator}>
          <span className={styles.liveDot}/>
          <span>Live</span>
        </div>
      </div>
    </header>
  )
}
