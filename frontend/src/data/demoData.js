export const demoDashboard = {
  user: {
    name: 'Adarsh Singh',
    initials: 'AS',
    greeting: 'Good evening',
  },
  balance: 18420.5,
  income: 46200,
  spent: 27779.5,
  saved: 7840,
  monthlyChange: 12.4,
  financialHealth: 82,
  safeToSpend: 9340,
  streak: 7,
  insight: {
    title: 'You are ahead of your plan',
    body: 'Your spending is 11% lower than this time last month. Keep your dining budget under ₹1,140 this week to stay on track.',
    action: 'Review plan',
  },
  cashflow: [
    { label: '1', income: 3000, spend: 1600 },
    { label: '5', income: 800, spend: 2700 },
    { label: '10', income: 4200, spend: 2200 },
    { label: '15', income: 1200, spend: 3400 },
    { label: '20', income: 7000, spend: 2600 },
    { label: '25', income: 2300, spend: 3100 },
    { label: '30', income: 4800, spend: 1850 },
  ],
}

export const demoTransactions = [
  { id: 'txn-1001', merchant: 'Blinkit', category: 'Groceries', account: 'HDFC Platinum', amount: -1840, date: 'Today, 10:24 AM', icon: 'basket', color: 'lime', type: 'expense', note: 'Weekly kitchen stock-up', private: false },
  { id: 'txn-1002', merchant: 'Acme Labs', category: 'Salary', account: 'HDFC Platinum', amount: 46200, date: '01 Sep, 09:00 AM', icon: 'briefcase', color: 'violet', type: 'income', note: 'September payroll', private: false },
  { id: 'txn-1003', merchant: 'Uber', category: 'Transport', account: 'UPI', amount: -318, date: 'Yesterday, 08:42 PM', icon: 'car', color: 'orange', type: 'expense', note: 'Ride home', private: false },
  { id: 'txn-1004', merchant: 'Spotify', category: 'Subscriptions', account: 'HDFC Platinum', amount: -119, date: 'Yesterday, 12:01 PM', icon: 'music', color: 'pink', type: 'expense', note: 'Duo plan', private: false },
  { id: 'txn-1005', merchant: 'Blue Tokai', category: 'Dining', account: 'UPI', amount: -485, date: '29 Aug, 03:18 PM', icon: 'coffee', color: 'cyan', type: 'expense', note: 'Coffee with Riya', private: true },
  { id: 'txn-1006', merchant: 'Groww', category: 'Investments', account: 'HDFC Platinum', amount: -2500, date: '28 Aug, 11:24 AM', icon: 'chart', color: 'blue', type: 'expense', note: 'Monthly mutual fund', private: false },
  { id: 'txn-1007', merchant: 'Amazon', category: 'Shopping', account: 'HDFC Platinum', amount: -1899, date: '26 Aug, 06:32 PM', icon: 'bag', color: 'purple', type: 'expense', note: 'Desk lamp and notebook', private: false },
]

export const demoBudgets = [
  { id: 'budget-1', category: 'Food & dining', spent: 3820, limit: 5500, color: '#bfef6a', icon: 'utensils', period: 'Monthly' },
  { id: 'budget-2', category: 'Shopping', spent: 4270, limit: 5000, color: '#d1b9ff', icon: 'bag', period: 'Monthly' },
  { id: 'budget-3', category: 'Transport', spent: 1680, limit: 2800, color: '#83d9ff', icon: 'car', period: 'Monthly' },
  { id: 'budget-4', category: 'Fun & leisure', spent: 2140, limit: 2500, color: '#ffb56b', icon: 'sparkle', period: 'Monthly' },
  { id: 'budget-5', category: 'Self care', spent: 980, limit: 1800, color: '#ff9ac2', icon: 'heart', period: 'Monthly' },
]

export const demoGoals = [
  { id: 'goal-1', name: 'Japan, 2027', emoji: '🗻', saved: 87400, target: 150000, monthly: 8500, date: 'Sep 2027', color: '#a78bfa' },
  { id: 'goal-2', name: 'Rainy day fund', emoji: '☔', saved: 42200, target: 60000, monthly: 5000, date: 'Mar 2027', color: '#70e2b2' },
  { id: 'goal-3', name: 'New studio setup', emoji: '🖥️', saved: 17800, target: 45000, monthly: 3000, date: 'Jan 2027', color: '#fbbf77' },
]

export const demoBills = [
  { id: 'bill-1', name: 'Netflix Premium', category: 'Entertainment', amount: 649, cadence: 'Monthly', due: 'Tomorrow', icon: 'play', color: 'red', active: true },
  { id: 'bill-2', name: 'Airtel Fiber', category: 'Utilities', amount: 999, cadence: 'Monthly', due: '04 Sep', icon: 'wifi', color: 'cyan', active: true },
  { id: 'bill-3', name: 'Gym membership', category: 'Health', amount: 1800, cadence: 'Monthly', due: '08 Sep', icon: 'dumbbell', color: 'lime', active: true },
  { id: 'bill-4', name: 'iCloud+', category: 'Storage', amount: 75, cadence: 'Monthly', due: '12 Sep', icon: 'cloud', color: 'blue', active: true },
]

export const categoryBreakdown = [
  { name: 'Food & dining', amount: 3820, value: 31, color: '#bfef6a' },
  { name: 'Shopping', amount: 4270, value: 24, color: '#cbb4ff' },
  { name: 'Transport', amount: 1680, value: 16, color: '#83d9ff' },
  { name: 'Subscriptions', amount: 1597, value: 11, color: '#ff9ac2' },
  { name: 'Everything else', amount: 2932, value: 18, color: '#ffb56b' },
]

export const categories = [
  'Groceries', 'Dining', 'Transport', 'Shopping', 'Subscriptions', 'Bills & utilities', 'Health', 'Travel', 'Education', 'Investments', 'Gifts', 'Other',
]

export const accounts = ['HDFC Platinum', 'UPI', 'SBI Savings', 'Cash', 'Business account']
