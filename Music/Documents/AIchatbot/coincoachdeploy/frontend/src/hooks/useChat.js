import { useState, useCallback, useRef } from 'react'
import { parseBudgetJSON, stripBudgetJSON } from '../utils/format'
import { api } from '../utils/api'
import { todayStr } from '../utils/dateUtils'
import { RATE_LIMIT } from '../utils/constants'

const INITIAL_MSG = {
  role: 'assistant',
  text: `Hey! 👋 I'm **CoinCoach** — your personal money buddy.\n\nI'll help you:\n• Track income and spending day by day\n• Roll up into weekly, monthly and yearly totals\n• Correct any mistakes — just tell me\n• Give personalised saving tips\n\n**What money did you receive or spend today?**\n\nJust talk naturally — "Today I got ₹500 and spent ₹200 on petrol"`,
}

export function useChat(user, summary, onEntryChanged) {
  const [messages, setMessages]         = useState([INITIAL_MSG])
  const [isLoading, setIsLoading]       = useState(false)
  const [callCount, setCallCount]       = useState(0)
  const [latestBudget, setLatestBudget] = useState(null)
  const historyRef = useRef([])

  const sendMessage = useCallback(async (userText) => {
    if (!userText.trim() || !user) return
    if (callCount >= RATE_LIMIT) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: '• Rate limit of 60 calls reached\n• Please refresh to continue'
      }])
      return
    }

    setMessages(prev => [...prev, { role: 'user', text: userText }])
    setIsLoading(true)
    historyRef.current = [...historyRef.current, { role: 'user', content: userText }]

    try {
      // Get latest summary for context
      let currentSummary = summary
      try { currentSummary = (await api.getSummary()) } catch {}

      const data = await api.chat(historyRef.current, currentSummary)
      const raw     = data.content
      const parsed  = parseBudgetJSON(raw)
      const display = stripBudgetJSON(raw)

      historyRef.current = [...historyRef.current, { role: 'assistant', content: raw }]
      setMessages(prev => [...prev, { role: 'assistant', text: display }])
      setCallCount(c => c + 1)

      // Save entry to Neon via API
      if (parsed?.entry) {
        const entry = {
          date:     parsed.entry.date || todayStr(),
          income:   Number(parsed.entry.income) || 0,
          expenses: parsed.entry.expenses || {},
          note:     parsed.entry.note || userText.slice(0, 120),
          action:   parsed.action || 'new',
        }
        await api.saveEntry(entry).catch(console.error)
        // Notify parent to refresh summary
        if (onEntryChanged) onEntryChanged()
      }

      if (parsed) setLatestBudget(parsed)

    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `• Error: ${err.message}\n• Please try again`
      }])
    } finally {
      setIsLoading(false)
    }
  }, [callCount, user, summary, onEntryChanged])

  const resetChat = useCallback(() => {
    setMessages([INITIAL_MSG])
    setCallCount(0)
    historyRef.current = []
  }, [])

  return { messages, isLoading, callCount, latestBudget, sendMessage, resetChat }
}
