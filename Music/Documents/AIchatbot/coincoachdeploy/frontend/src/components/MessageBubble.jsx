import React from 'react'
import { formatBubble } from '../utils/format'
import styles from '../styles/MessageBubble.module.css'

export default function MessageBubble({ role, text }) {
  const isBot = role === 'assistant'
  const html  = formatBubble(text)

  return (
    <div className={`${styles.msg} ${isBot ? styles.bot : styles.user}`}>
      {isBot && (
        <div className={styles.avatarBot}>
          <span>◈</span>
        </div>
      )}
      <div className={`${styles.bubble} ${isBot ? styles.bubbleBot : styles.bubbleUser}`}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  )
}
