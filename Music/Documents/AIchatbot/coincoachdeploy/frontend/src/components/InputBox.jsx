import React, { useState, useRef } from 'react'
import { EXPENSE_FIELDS, STORY_EXAMPLES, RATE_LIMIT } from '../utils/constants'
import styles from '../styles/InputBox.module.css'

export default function InputBox({ onSend, isLoading, callCount }) {
  const [value, setValue]       = useState('')
  const [suggestions, setSugg]  = useState([])
  const [showSugg, setShowSugg] = useState(false)
  const [activeIdx, setIdx]     = useState(-1)
  const [mode, setMode]         = useState('chat')
  const textareaRef = useRef(null)
  const pct = (callCount / RATE_LIMIT) * 100
  const remaining = RATE_LIMIT - callCount

  function filterSugg(val) {
    const low = val.toLowerCase().trim()
    if (!low) return EXPENSE_FIELDS
    return EXPENSE_FIELDS.filter(f => f.key.toLowerCase().includes(low))
  }

  function handleChange(e) {
    const val = e.target.value
    setValue(val)
    if (mode === 'chat' && val.length < 35) { setSugg(filterSugg(val)); setShowSugg(true) }
    else setShowSugg(false)
    setIdx(-1)
    autoResize(e.target)
  }

  function autoResize(el) {
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  function pickSugg(field) {
    setValue(field.key + ': ')
    setShowSugg(false)
    textareaRef.current?.focus()
    setTimeout(() => autoResize(textareaRef.current), 0)
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); return }
    if (e.key === 'Escape') { setShowSugg(false); return }
    if (!showSugg || !suggestions.length) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setIdx(i => Math.min(i+1, suggestions.length-1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setIdx(i => Math.max(i-1, 0)) }
    if (e.key === 'Tab') { e.preventDefault(); const t = suggestions[activeIdx>=0?activeIdx:0]; if(t) pickSugg(t) }
  }

  function submit() {
    const t = value.trim()
    if (!t || isLoading || callCount >= RATE_LIMIT) return
    onSend(t)
    setValue('')
    setShowSugg(false)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  function pasteExample() {
    const ex = STORY_EXAMPLES[Math.floor(Math.random() * STORY_EXAMPLES.length)]
    setValue(ex)
    setMode('story')
    setShowSugg(false)
    textareaRef.current?.focus()
    setTimeout(() => autoResize(textareaRef.current), 0)
  }

  const exhausted = callCount >= RATE_LIMIT

  return (
    <div className={styles.wrap}>
      {showSugg && suggestions.length > 0 && mode === 'chat' && (
        <div className={styles.suggBox}>
          {suggestions.map((f, i) => (
            <div
              key={f.key}
              className={`${styles.suggItem} ${i === activeIdx ? styles.active : ''}`}
              onMouseDown={() => pickSugg(f)}
            >
              <span className={styles.suggIcon}>{f.icon}</span>
              <span className={styles.suggKey}>{f.key}</span>
              <span className={styles.suggHint}>{f.hint}</span>
            </div>
          ))}
        </div>
      )}

      <div className={styles.modeBar}>
        <button className={`${styles.modeBtn} ${mode==='chat'?styles.modeOn:''}`}
          onClick={() => { setMode('chat'); setShowSugg(false) }}>
          ⚡ Quick
        </button>
        <button className={`${styles.modeBtn} ${mode==='story'?styles.modeOn:''}`}
          onClick={() => { setMode('story'); setShowSugg(false) }}>
          📖 Story
        </button>
        {mode === 'story' && (
          <button className={styles.exBtn} onClick={pasteExample}>try example</button>
        )}
        <div className={styles.rateRight}>
          <div className={styles.rateTrack}>
            <div className={styles.rateFill} style={{
              width:`${pct}%`,
              background: pct>80?'var(--danger)':pct>55?'var(--warn)':'var(--accent)'
            }}/>
          </div>
          <span className={styles.rateTxt} style={{color:pct>80?'var(--danger)':'var(--text3)'}}>
            {remaining} left
          </span>
        </div>
      </div>

      <div className={styles.inputRow}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={value}
          onChange={handleChange}
          onFocus={() => { if(mode==='chat'){setSugg(filterSugg(value));setShowSugg(true)} }}
          onBlur={() => setTimeout(()=>setShowSugg(false),160)}
          onKeyDown={handleKey}
          placeholder={
            exhausted ? 'Rate limit reached. Refresh to continue.' :
            mode==='story'
              ? 'Tell me your day — "Today I received ₹500 and spent ₹200 on petrol…"'
              : 'Type a field like "Petrol: ₹200" or ask anything…'
          }
          rows={mode==='story'?3:1}
          disabled={isLoading || exhausted}
        />
        <button className={styles.sendBtn} onClick={submit}
          disabled={isLoading || !value.trim() || exhausted}>
          {isLoading
            ? <div className={styles.spinner}/>
            : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          }
        </button>
      </div>
    </div>
  )
}
