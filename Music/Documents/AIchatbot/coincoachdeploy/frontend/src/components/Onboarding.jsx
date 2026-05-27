import React, { useState } from 'react'
import styles from '../styles/Onboarding.module.css'

export default function Onboarding({ onComplete }) {
  const [name, setName] = useState('')

  function handleStart() {
    const n = name.trim()
    if (n.length < 2) return
    onComplete({ name: n, createdAt: new Date().toISOString() })
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <div className={styles.logo}>Coin<span>Coach</span></div>
        <div className={styles.subtitle}>Your personal money buddy 💚</div>
        <div className={styles.question}>Hey! What should I call you? 👋</div>
        <input
          className={styles.input}
          placeholder="Your name…"
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleStart()}
          autoFocus
        />
        <button
          className={styles.nextBtn}
          onClick={handleStart}
          disabled={name.trim().length < 2}
        >
          Let's go! 🚀
        </button>
        <div className={styles.privacy}>🔒 Your data stays on your device only</div>
      </div>
    </div>
  )
}
