const router = require('express').Router()
const auth   = require('../middleware/auth')
const pool   = require('../db/pool')

// All entry routes require auth
router.use(auth)

// ── UPSERT ENTRY (new or correct) ────────────────────────
// action: 'new' = merge same-day, 'correct' = full replace
router.post('/', async (req, res) => {
  const { date, income, expenses, note, action } = req.body
  const userId = req.user.id

  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return res.status(400).json({ error: 'Valid date (YYYY-MM-DD) required' })
  }

  try {
    if (action === 'correct') {
      // REPLACE — full overwrite of that date
      const result = await pool.query(`
        INSERT INTO entries (user_id, entry_date, income, expenses, note, corrected, updated_at)
        VALUES ($1, $2, $3, $4, $5, true, NOW())
        ON CONFLICT (user_id, entry_date)
        DO UPDATE SET
          income     = EXCLUDED.income,
          expenses   = EXCLUDED.expenses,
          note       = EXCLUDED.note,
          corrected  = true,
          updated_at = NOW()
        RETURNING *
      `, [userId, date, income || 0, JSON.stringify(expenses || {}), note || ''])

      return res.json({ entry: formatEntry(result.rows[0]), action: 'corrected' })

    } else {
      // MERGE — add income, add to each expense category
      const result = await pool.query(`
        INSERT INTO entries (user_id, entry_date, income, expenses, note, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (user_id, entry_date)
        DO UPDATE SET
          income     = entries.income + EXCLUDED.income,
          expenses   = (
            SELECT jsonb_object_agg(
              key,
              COALESCE((entries.expenses ->> key)::numeric, 0) +
              COALESCE((EXCLUDED.expenses ->> key)::numeric, 0)
            )
            FROM jsonb_object_keys(entries.expenses || EXCLUDED.expenses) AS key
          ),
          note       = CASE
            WHEN entries.note = '' THEN EXCLUDED.note
            ELSE entries.note || ' | ' || EXCLUDED.note
          END,
          updated_at = NOW()
        RETURNING *
      `, [userId, date, income || 0, JSON.stringify(expenses || {}), note || ''])

      return res.json({ entry: formatEntry(result.rows[0]), action: 'saved' })
    }

  } catch (err) {
    console.error('Entry upsert error:', err.message)
    res.status(500).json({ error: 'Failed to save entry' })
  }
})

// ── GET ENTRIES — with flexible range filters ─────────────
router.get('/', async (req, res) => {
  const userId = req.user.id
  const { from, to, month, year, limit = 100 } = req.query

  try {
    let query, params

    if (month) {
      // e.g. month=2025-05
      query = `
        SELECT * FROM entries
        WHERE user_id = $1
          AND DATE_TRUNC('month', entry_date) = DATE_TRUNC('month', $2::date)
        ORDER BY entry_date DESC
      `
      params = [userId, month + '-01']

    } else if (year) {
      query = `
        SELECT * FROM entries
        WHERE user_id = $1
          AND EXTRACT(YEAR FROM entry_date) = $2
        ORDER BY entry_date DESC
      `
      params = [userId, parseInt(year)]

    } else if (from && to) {
      query = `
        SELECT * FROM entries
        WHERE user_id = $1
          AND entry_date BETWEEN $2 AND $3
        ORDER BY entry_date DESC
      `
      params = [userId, from, to]

    } else {
      // Default: last N entries
      query = `
        SELECT * FROM entries
        WHERE user_id = $1
        ORDER BY entry_date DESC
        LIMIT $2
      `
      params = [userId, parseInt(limit)]
    }

    const result = await pool.query(query, params)
    res.json({ entries: result.rows.map(formatEntry) })

  } catch (err) {
    console.error('Get entries error:', err.message)
    res.status(500).json({ error: 'Failed to fetch entries' })
  }
})

// ── GET SUMMARY — aggregated stats ───────────────────────
router.get('/summary', async (req, res) => {
  const userId = req.user.id
  const today  = new Date().toISOString().slice(0, 10)
  const thisMonth = today.slice(0, 7)
  const thisYear  = today.slice(0, 4)

  try {
    // Today
    const todayRes = await pool.query(`
      SELECT income, expenses FROM entries
      WHERE user_id = $1 AND entry_date = $2
    `, [userId, today])

    // This month aggregated
    const monthRes = await pool.query(`
      SELECT
        SUM(income) as total_income,
        jsonb_object_agg(
          cat_key,
          cat_sum
        ) FILTER (WHERE cat_key IS NOT NULL) as expenses,
        COUNT(*) as entry_count
      FROM entries,
        LATERAL (
          SELECT key as cat_key, SUM(value::numeric) as cat_sum
          FROM jsonb_each_text(expenses)
          GROUP BY key
        ) cats
      WHERE user_id = $1
        AND DATE_TRUNC('month', entry_date) = DATE_TRUNC('month', $2::date)
    `, [userId, thisMonth + '-01'])

    // This year
    const yearRes = await pool.query(`
      SELECT
        SUM(income) as total_income,
        SUM((SELECT SUM(v::numeric) FROM jsonb_each_text(expenses) AS t(k,v))) as total_expenses,
        COUNT(*) as entry_count
      FROM entries
      WHERE user_id = $1
        AND EXTRACT(YEAR FROM entry_date) = $2
    `, [userId, parseInt(thisYear)])

    // Recent 7 entries
    const recentRes = await pool.query(`
      SELECT * FROM entries
      WHERE user_id = $1
      ORDER BY entry_date DESC
      LIMIT 7
    `, [userId])

    // Build month totals
    const mRow = monthRes.rows[0] || {}
    const monthExpenses = mRow.expenses || {}
    const monthIncome   = Number(mRow.total_income) || 0
    const monthSpent    = Object.values(monthExpenses).reduce((a,b)=>a+Number(b),0)

    // Today data
    const tRow = todayRes.rows[0] || {}
    const todayIncome  = Number(tRow.income) || 0
    const todayExpenses = tRow.expenses || {}
    const todaySpent   = Object.values(todayExpenses).reduce((a,b)=>a+Number(b),0)

    // Year totals
    const yRow = yearRes.rows[0] || {}
    const yearIncome  = Number(yRow.total_income) || 0
    const yearSpent   = Number(yRow.total_expenses) || 0

    res.json({
      today: {
        date:           today,
        totalIncome:    todayIncome,
        totalExpenses:  todaySpent,
        balance:        todayIncome - todaySpent,
        expenses:       todayExpenses,
        entryCount:     todayRes.rows.length,
      },
      thisMonth: {
        key:            thisMonth,
        totalIncome:    monthIncome,
        totalExpenses:  monthSpent,
        balance:        monthIncome - monthSpent,
        savingsRate:    monthIncome > 0 ? +((( monthIncome - monthSpent) / monthIncome)*100).toFixed(1) : 0,
        expenses:       monthExpenses,
        entryCount:     Number(mRow.entry_count) || 0,
      },
      thisYear: {
        key:            thisYear,
        totalIncome:    yearIncome,
        totalExpenses:  yearSpent,
        balance:        yearIncome - yearSpent,
        savingsRate:    yearIncome > 0 ? +(((yearIncome - yearSpent) / yearIncome)*100).toFixed(1) : 0,
        entryCount:     Number(yRow.entry_count) || 0,
      },
      recentEntries: recentRes.rows.map(formatEntry),
    })

  } catch (err) {
    console.error('Summary error:', err.message)
    res.status(500).json({ error: 'Failed to fetch summary' })
  }
})

// ── DELETE ENTRY ──────────────────────────────────────────
router.delete('/:date', async (req, res) => {
  const { date } = req.params
  const userId = req.user.id
  try {
    await pool.query(
      'DELETE FROM entries WHERE user_id = $1 AND entry_date = $2',
      [userId, date]
    )
    res.json({ message: 'Entry deleted' })
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete entry' })
  }
})

// ── Helper ────────────────────────────────────────────────
function formatEntry(row) {
  return {
    id:        row.id,
    date:      row.entry_date instanceof Date
      ? row.entry_date.toISOString().slice(0,10)
      : String(row.entry_date).slice(0,10),
    income:    Number(row.income),
    expenses:  row.expenses || {},
    note:      row.note || '',
    corrected: row.corrected || false,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

module.exports = router
