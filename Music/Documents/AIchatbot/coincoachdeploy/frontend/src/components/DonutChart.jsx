import React, { useMemo } from 'react'
import { CHART_COLORS } from '../utils/constants'
import { formatINR } from '../utils/format'
import styles from '../styles/DonutChart.module.css'

export default function DonutChart({ expenses }) {
  const entries = Object.entries(expenses)
  const total   = entries.reduce((s, [, v]) => s + v, 0)

  const segments = useMemo(() => {
    const cx = 72, cy = 72, r = 54, sw = 17
    const circ = 2 * Math.PI * r
    const gap  = 1.5
    const usable = circ - entries.length * gap
    let offset = 0
    return entries.map(([cat, val], i) => {
      const seg = (val / total) * usable
      const dashOffset = -(offset - circ / 4)
      offset += seg + gap
      return { cat, val, seg, circ, dashOffset, color: CHART_COLORS[i % CHART_COLORS.length] }
    })
  }, [expenses])

  return (
    <div className={styles.wrap}>
      <svg viewBox="0 0 144 144" className={styles.svg}>
        {/* Background ring */}
        <circle cx="72" cy="72" r="54" fill="none" stroke="#2e2d28" strokeWidth="17" />

        {segments.map(({ cat, seg, circ, dashOffset, color }, i) => (
          <circle
            key={cat}
            cx="72" cy="72" r="54"
            fill="none"
            stroke={color}
            strokeWidth="17"
            strokeDasharray={`${seg} ${circ - seg}`}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
          />
        ))}

        {/* Center label */}
        <text x="72" y="65" textAnchor="middle" fontFamily="DM Serif Display,serif" fontSize="10" fill="#8a877e">
          {formatINR(total)}
        </text>
        <text x="72" y="80" textAnchor="middle" fontFamily="DM Sans,sans-serif" fontSize="8" fill="#5a5950">
          total spend
        </text>
      </svg>

      <div className={styles.legend}>
        {segments.map(({ cat, val, color }) => (
          <div key={cat} className={styles.legendRow}>
            <span className={styles.legendLeft}>
              <span className={styles.dot} style={{ background: color }} />
              {cat}
            </span>
            <span className={styles.legendVal}>{formatINR(val)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
