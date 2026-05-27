export const EXPENSE_FIELDS = [
  { key:'Money received',        hint:'Income, funds, any money in',          icon:'💰' },
  { key:'Eating outside',        hint:'Restaurants, Swiggy, Zomato, food',    icon:'🍛' },
  { key:'Travelling',            hint:'Petrol, auto, cab, bus, train, fuel',  icon:'🚗' },
  { key:'Grocery',               hint:'Groceries, vegetables, kirana',        icon:'🛒' },
  { key:'Education',             hint:'Books, fees, stationery, courses',     icon:'📚' },
  { key:'Entertainment',         hint:'Movies, games, outings, parties',      icon:'🎮' },
  { key:'Recharge bill',         hint:'Mobile, internet, DTH, wifi',         icon:'📱' },
  { key:'Subscriptions',         hint:'Netflix, Spotify, Prime, apps',        icon:'📺' },
  { key:'Shopping',              hint:'Clothes, shoes, Amazon, Flipkart',    icon:'🛍️' },
  { key:'Medical',               hint:'Medicines, doctor, hospital',          icon:'💊' },
  { key:'Unexpected expense',    hint:'Surprise spends, miscellaneous',       icon:'🎲' },
  { key:'Saving',                hint:'Money set aside, FD, SIP',            icon:'🏦' },
  { key:'Rent',                  hint:'Rent, PG, hostel',                    icon:'🏠' },
  { key:'Electricity bill',      hint:'EB bill, current, power',             icon:'⚡' },
  { key:'Water bill',            hint:'Water charges',                       icon:'💧' },
  { key:'EMI',                   hint:'Loan EMIs, credit repayments',        icon:'📋' },
]

export const STORY_EXAMPLES = [
  "Today I received ₹500 and spent ₹80 on lunch and ₹150 on petrol",
  "Got ₹2000, paid ₹800 rent and ₹200 on groceries today",
  "Today I got ₹300, ate outside for ₹120 and bought a book for ₹80",
  "I spent ₹60 on coffee, ₹200 on Swiggy and saved ₹100 today",
]

export const ICON_MAP = Object.fromEntries(EXPENSE_FIELDS.map(f => [f.key, f.icon]))

export const CHART_COLORS = [
  '#a3e635','#fbbf24','#4ade80','#f87171',
  '#60a5fa','#c084fc','#fb923c','#34d399',
  '#f9a8d4','#a78bfa','#67e8f9','#fde68a',
]

export const RATE_LIMIT = 60
export const API_BASE   = '/api'
