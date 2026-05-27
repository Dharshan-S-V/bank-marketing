// Auto-runs on server start — safe to run multiple times (IF NOT EXISTS)
const pool = require('./pool')

async function migrate() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name        VARCHAR(100) NOT NULL,
        email       VARCHAR(255) UNIQUE NOT NULL,
        password    VARCHAR(255) NOT NULL,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW()
      )
    `)
    await pool.query(`
      CREATE TABLE IF NOT EXISTS entries (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        entry_date  DATE NOT NULL,
        income      NUMERIC(12,2) DEFAULT 0,
        expenses    JSONB DEFAULT '{}',
        note        TEXT DEFAULT '',
        corrected   BOOLEAN DEFAULT false,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(user_id, entry_date)
      )
    `)
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_entries_user_date ON entries(user_id, entry_date DESC)`)
    await pool.query(`CREATE INDEX IF NOT EXISTS idx_entries_user_month ON entries(user_id, DATE_TRUNC('month', entry_date))`)
    console.log('✅ Database schema ready')
  } catch (err) {
    console.error('⚠️  Migration warning:', err.message)
  }
}

migrate()
module.exports = migrate
