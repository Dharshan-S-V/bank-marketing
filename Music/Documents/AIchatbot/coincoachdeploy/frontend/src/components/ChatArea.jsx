import React, { useRef, useEffect, useState } from 'react'
import MessageBubble from './MessageBubble'
import InputBox from './InputBox'
import styles from '../styles/ChatArea.module.css'

const QUICK_REPLIES = [
  'Today I received ₹500 and spent ₹200 on petrol and ₹150 on food',
  'I got ₹2000 today and paid ₹800 on rent',
  'Show my monthly summary',
  'Give me saving tips',
]

export default function ChatArea({ messages, isLoading, callCount, onSend, user }) {
  const bottomRef = useRef(null)
  const [usedQuick, setUsedQuick] = useState(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior:'smooth' })
  }, [messages, isLoading])

  return (
    <div className={styles.chatArea}>
      <div className={styles.messages}>
        {messages.map((msg,i) => (
          <MessageBubble key={i} role={msg.role} text={msg.text} />
        ))}
        {isLoading && (
          <div className={styles.typingRow}>
            <div className={styles.avatar}>C</div>
            <div className={styles.typingBubble}><span/><span/><span/></div>
          </div>
        )}
        <div ref={bottomRef}/>
      </div>

      {!usedQuick && messages.length <= 1 && (
        <div className={styles.quickReplies}>
          <span className={styles.quickLabel}>Quick start:</span>
          {QUICK_REPLIES.map(q => (
            <button key={q} className={styles.qr}
              onClick={() => { onSend(q); setUsedQuick(true) }}>
              {q}
            </button>
          ))}
        </div>
      )}

      <InputBox onSend={onSend} isLoading={isLoading} callCount={callCount} />
    </div>
  )
}
