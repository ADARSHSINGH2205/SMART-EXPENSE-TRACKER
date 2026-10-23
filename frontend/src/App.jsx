import { useEffect, useMemo, useRef, useState } from 'react'
import { payarcApi } from './api/client'
import {
  accounts,
  categories,
  categoryBreakdown,
  demoBills,
  demoBudgets,
  demoDashboard,
  demoGoals,
  demoTransactions,
} from './data/demoData'

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: 'grid' },
  { id: 'transactions', label: 'Transactions', icon: 'receipt' },
  { id: 'budgets', label: 'Budgets', icon: 'pie' },
  { id: 'goals', label: 'Goals', icon: 'target' },
  { id: 'bills', label: 'Recurring', icon: 'repeat' },
  { id: 'tools', label: 'Tools & data', icon: 'settings' },
]

const INITIAL_ASSISTANT_MESSAGES = [{
  id: 'hello',
  role: 'assistant',
  text: 'Hi Adarsh Singh - I reviewed this month\'s cash flow. You are building momentum: planned bills are covered and your savings rate is healthy.',
  suggestions: ['How can I save more?', 'What is unusual?', 'Plan my next week'],
}]

function money(value, compact) {
  const amount = Math.abs(Number(value) || 0)
  const formatted = new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: compact ? 1 : 0,
    notation: compact ? 'compact' : 'standard',
  }).format(amount)
  return (value < 0 ? '−' : '') + '₹' + formatted
}

function percent(value, total) {
  return Math.min(100, Math.round((Number(value) / Number(total || 1)) * 100))
}

function healthScore(value) {
  if (typeof value === 'object' && value) return Number(value.score) || 0
  return Number(value) || 0
}

function readableDate(value, fallback) {
  if (!value || typeof value !== 'string') return fallback || '—'
  if (!/^\d{4}-\d{2}-\d{2}/.test(value)) return value
  const parsed = new Date(value + (value.length === 10 ? 'T12:00:00' : ''))
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(parsed)
}

function getPayload(payload, key, fallback) {
  if (!payload) return fallback
  if (Array.isArray(payload)) return payload
  return payload[key] || payload.data || payload
}

function iconPaths(name) {
  const paths = {
    arrow: <path d="m5 12 14-7-5 14-2.7-5.3L5 12Z M11.3 13.7 19 5" />,
    arrowUp: <path d="M12 19V5m0 0-5 5m5-5 5 5" />,
    bag: <><path d="M6 8h12l1 12H5L6 8Z" /><path d="M9 8a3 3 0 0 1 6 0" /></>,
    bank: <><path d="m3 10 9-6 9 6" /><path d="M5 10v8m4-8v8m6-8v8m4-8v8M3 20h18" /></>,
    basket: <><path d="M4 10h16l-1.5 9h-13L4 10Z" /><path d="m8 10 2-5m6 5-2-5M8 14h8" /></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
    bolt: <path d="m13 2-9 12h7l-1 8 9-12h-7l1-8Z" />,
    briefcase: <><path d="M4 7h16v12H4z" /><path d="M9 7V5h6v2M4 12h16" /><path d="M10 12h4" /></>,
    calendar: <><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M8 3v4m8-4v4M4 10h16" /></>,
    car: <><path d="m5 16 1.5-6h11l1.5 6v3H5v-3Z" /><path d="M7 19v2m10-2v2M5 14h14" /><circle cx="8" cy="16" r="1" /><circle cx="16" cy="16" r="1" /></>,
    chart: <><path d="M4 19V5m0 14h16" /><path d="m7 15 4-4 3 2 5-6" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m9 18 6-6-6-6" />,
    chevronDown: <path d="m6 9 6 6 6-6" />,
    cloud: <path d="M7 18a4 4 0 0 1 .4-8A5 5 0 0 1 17 11a3.5 3.5 0 0 1-.5 7H7Z" />,
    coffee: <><path d="M5 8h11v9a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V8Z" /><path d="M16 10h1a2 2 0 0 1 0 4h-1M4 5h13" /></>,
    dots: <><circle cx="5" cy="12" r="1" fill="currentColor" /><circle cx="12" cy="12" r="1" fill="currentColor" /><circle cx="19" cy="12" r="1" fill="currentColor" /></>,
    dumbbell: <><path d="M6 9v6m12-6v6M4 10v4m16-4v4M6 12h12" /></>,
    edit: <><path d="M12 20h8" /><path d="M16 3.5a2.1 2.1 0 0 1 3 3L8 17l-4 1 1-4L16 3.5Z" /></>,
    file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6m-6 3h6" /></>,
    grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    heart: <path d="M20.8 8.5c0 6-8.8 11-8.8 11S3.2 14.5 3.2 8.5A4.3 4.3 0 0 1 11 6l1 1 1-1a4.3 4.3 0 0 1 7.8 2.5Z" />,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.6 2.6 0 1 1 4.2 2.1c-1.2.9-1.7 1.4-1.7 2.9M12 17h.01" /></>,
    key: <><circle cx="8" cy="15" r="3" /><path d="m10.2 12.8 8-8 2 2-1.5 1.5 1.5 1.5-2 2-1.5-1.5-4.6 4.6" /></>,
    lock: <><rect x="4" y="10" width="16" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" /></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    moon: <path d="M20.5 15.5A8.5 8.5 0 0 1 8.5 3.5 8.5 8.5 0 1 0 20.5 15.5Z" />,
    music: <><path d="M9 18V6l10-2v12" /><circle cx="6" cy="18" r="3" /><circle cx="16" cy="16" r="3" /></>,
    paperclip: <path d="m20.5 11.5-8.8 8.8a5 5 0 0 1-7.1-7.1l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-2.8-2.8l8.3-8.3" />,
    pie: <><path d="M12 3v9h9A9 9 0 1 1 12 3Z" /><path d="M15 3.5A7 7 0 0 1 20.5 9H15V3.5Z" /></>,
    play: <path d="m8 5 11 7-11 7V5Z" />,
    plus: <path d="M12 5v14M5 12h14" />,
    receipt: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z" /><path d="M9 8h6M9 12h6M9 16h3" /></>,
    repeat: <><path d="M17 2l4 4-4 4" /><path d="M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4" /><path d="M21 13v2a3 3 0 0 1-3 3H3" /></>,
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
    send: <path d="m3 11 18-8-6 18-3.5-6.5L3 11Zm8.5 3.5L21 3" />,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.1 2.1-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5v.2h-3v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1-2.1-2.1.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H5.3v-3h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 2.1-2.1.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5v-.2h3v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1 2.1 2.1-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.2v3h-.2a1.7 1.7 0 0 0-1.4 1Z" /></>,
    shield: <><path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z" /><path d="m8.5 12 2.2 2.2 4.8-5" /></>,
    sparkle: <><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" /><path d="m19 16 .6 2.4L22 19l-2.4.6L19 22l-.6-2.4L16 19l2.4-.6L19 16Z" /></>,
    target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 4V2m0 20v-2m8-8h2M2 12h2" /></>,
    trash: <><path d="M4 7h16M10 11v6m4-6v6M9 7l1-3h4l1 3m-9 0 1 14h10l1-14" /></>,
    trend: <><path d="M4 17 10 11l4 4 6-8" /><path d="M15 7h5v5" /></>,
    upload: <><path d="M12 16V4m0 0-4 4m4-4 4 4M5 15v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4" /></>,
    utensils: <><path d="M7 3v8M4 3v4a3 3 0 0 0 6 0V3M7 11v10M16 3v18M16 3c3 1 3 7 0 8" /></>,
    vault: <><path d="M4 4h16v16H4z" /><circle cx="12" cy="12" r="4" /><path d="M12 8v8m-4-4h8" /></>,
    wallet: <><path d="M5 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h11" /><path d="M16 13h5M16 13a1 1 0 1 0 0 .01" /></>,
    wifi: <><path d="M4 9a12 12 0 0 1 16 0M7 12a8 8 0 0 1 10 0m-7 3a4 4 0 0 1 4 0" /><circle cx="12" cy="19" r=".8" fill="currentColor" /></>,
    x: <path d="m6 6 12 12M18 6 6 18" />,
  }
  return paths[name] || paths.sparkle
}

function Icon({ name, size, stroke, className }) {
  return <svg className={'icon ' + (className || '')} width={size || 20} height={size || 20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke || 1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths(name)}</svg>
}

function IconButton({ icon, label, className, ...props }) {
  return <button className={'icon-button ' + (className || '')} aria-label={label} title={label} {...props}><Icon name={icon} /></button>
}

function Avatar({ initials, size }) {
  return <span className={'avatar avatar-' + (size || 'normal')} aria-label={(initials || 'AK') + ' profile'}>{initials || 'AK'}</span>
}

function StatusDot({ status }) {
  return <span className={'status-dot status-' + (status || 'online')} aria-label={status || 'online'} />
}

function App() {
  const [activePage, setActivePage] = useState('overview')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [expenseOpen, setExpenseOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [syncState, setSyncState] = useState('connecting')
  const [syncMessage, setSyncMessage] = useState('')
  const [toast, setToast] = useState(null)
  const [dashboard, setDashboard] = useState(demoDashboard)
  const [transactions, setTransactions] = useState(demoTransactions)
  const [budgets, setBudgets] = useState(demoBudgets)
  const [goals, setGoals] = useState(demoGoals)
  const [bills, setBills] = useState(demoBills)
  async function refreshWorkspace(showLoading = false) {
    if (showLoading) setIsLoading(true)
    const results = await Promise.allSettled([payarcApi.getDashboard(), payarcApi.getTransactions(), payarcApi.getBudgets(), payarcApi.getGoals(), payarcApi.getBills()])
    const successful = results.filter((item) => item.status === 'fulfilled').length
    if (results[0].status === 'fulfilled') {
      const data = getPayload(results[0].value, 'dashboard', {})
      setDashboard((current) => ({ ...current, ...data }))
      if (data.budgets) setBudgets(data.budgets)
      if (data.goals) setGoals(data.goals)
      if (data.bills) setBills(data.bills)
      if (data.recentTransactions) setTransactions(data.recentTransactions)
    }
    if (results[1].status === 'fulfilled') setTransactions(getPayload(results[1].value, 'transactions', []))
    if (results[2].status === 'fulfilled') setBudgets(getPayload(results[2].value, 'budgets', []))
    if (results[3].status === 'fulfilled') setGoals(getPayload(results[3].value, 'goals', []))
    if (results[4].status === 'fulfilled') setBills(getPayload(results[4].value, 'bills', []))
    setIsLoading(false)
    setSyncState(successful === results.length ? 'online' : successful ? 'partial' : 'preview')
  }

  useEffect(() => { refreshWorkspace(true) }, [])

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(function () { setToast(null) }, 3400)
    return function () { window.clearTimeout(timer) }
  }, [toast])

  useEffect(() => {
    function handleShortcut(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setAssistantOpen(true)
      }
    }
    window.addEventListener('keydown', handleShortcut)
    return function () { window.removeEventListener('keydown', handleShortcut) }
  }, [])

  function notify(message, type) {
    setToast({ message: message, type: type || 'success' })
  }

  async function handleCreateExpense(input) {
    const isIncome = input.kind === 'income'
    const amount = Number(input.amount)
    const signedAmount = isIncome ? amount : -amount
    const optimistic = {
      id: 'local-' + Date.now(),
      merchant: input.merchant || (isIncome ? 'New income' : 'Unlabelled expense'),
      category: input.category,
      account: input.account,
      amount: signedAmount,
      date: 'Just now',
      icon: isIncome ? 'briefcase' : 'wallet',
      color: isIncome ? 'violet' : 'lime',
      type: isIncome ? 'income' : 'expense',
      note: input.note,
      private: input.private,
    }
    setTransactions(function (current) { return [optimistic].concat(current) })
    setDashboard(function (current) {
      return {
        ...current,
        balance: current.balance + signedAmount,
        income: current.income + (isIncome ? amount : 0),
        spent: current.spent + (isIncome ? 0 : amount),
      }
    })
    setExpenseOpen(false)
    notify((isIncome ? 'Income' : 'Expense') + ' saved to your private ledger')
    try {
      const response = await payarcApi.createTransaction({
        merchant: optimistic.merchant,
        category: input.category,
        account: input.account,
        amount: amount,
        type: optimistic.type,
        note: input.note,
        is_private: input.private,
        transaction_date: new Date().toISOString(),
      })
      const created = getPayload(response, 'transaction', null)
      if (created && created.id && input.receipt) {
        const receipt = await payarcApi.uploadReceipt(created.id, input.receipt)
        if (receipt.ocr_text) notify(`Receipt saved and text extracted with ${receipt.ocr_provider || 'OCR'}`)
        else notify(receipt.ocr_error || 'Receipt saved. OCR needs Tesseract or a working Gemini connection.', 'neutral')
      }
      if (created && created.id) {
        setTransactions(function (current) {
          return current.map(function (item) { return item.id === optimistic.id ? { ...optimistic, ...created } : item })
        })
        await refreshWorkspace()
        setSyncState('online')
      }
    } catch {
      setSyncState(function (state) { return state === 'online' ? 'partial' : state })
    }
  }

  async function handleBillToggle(id) {
    const bill = bills.find(function (item) { return item.id === id })
    if (!bill) return
    const next = !bill.active
    setBills(function (current) { return current.map(function (item) { return item.id === id ? { ...item, active: next } : item }) })
    notify(bill.name + (next ? ' will be tracked' : ' is paused'), next ? 'success' : 'neutral')
    try {
      await payarcApi.updateBill(id, { active: next })
    } catch {
      setSyncState(function (state) { return state === 'online' ? 'partial' : state })
    }
  }

  async function handleDeleteTransaction(id) {
    if (!window.confirm('Delete this transaction? This permanently removes it from dashboard totals, analytics, budgets, and reports.')) return
    try {
      await payarcApi.deleteTransaction(id)
      await refreshWorkspace()
      notify('Transaction deleted and dashboard recalculated')
    } catch (error) { notify(error.message || 'Could not delete transaction', 'neutral') }
  }

  function switchPage(page) {
    setActivePage(page)
    setSidebarOpen(false)
  }

  return (
    <div className="payarc-app">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <Sidebar activePage={activePage} onNavigate={switchPage} open={sidebarOpen} onClose={function () { setSidebarOpen(false) }} onVault={function () { switchPage('vault') }} />
      <main className="main-content">
        <Topbar syncState={syncState} syncMessage={syncMessage} onOpenMenu={function () { setSidebarOpen(true) }} onOpenAssistant={function () { setAssistantOpen(true) }} onAddExpense={function () { setExpenseOpen(true) }} />
        {isLoading ? <DashboardSkeleton /> : <section className="page-wrap" aria-live="polite">
          {activePage === 'overview' && <OverviewPage dashboard={dashboard} transactions={transactions} budgets={budgets} goals={goals} onAddExpense={function () { setExpenseOpen(true) }} onGoTo={switchPage} />}
          {activePage === 'transactions' && <TransactionsPage transactions={transactions} onAddExpense={function () { setExpenseOpen(true) }} onDelete={handleDeleteTransaction} />}
          {activePage === 'budgets' && <BudgetsPage budgets={budgets} onAddExpense={function () { setExpenseOpen(true) }} />}
          {activePage === 'goals' && <GoalsPage goals={goals} notify={notify} />}
          {activePage === 'bills' && <BillsPage bills={bills} onToggle={handleBillToggle} />}
          {activePage === 'vault' && <PrivacyVaultPage notify={notify} />}
          {activePage === 'tools' && <ToolsPage notify={notify} />}
        </section>}
      </main>
      <AssistantDrawer open={assistantOpen} onClose={function () { setAssistantOpen(false) }} dashboard={dashboard} transactions={transactions} onAddExpense={function () { setAssistantOpen(false); setExpenseOpen(true) }} />
      <QuickExpenseModal open={expenseOpen} onClose={function () { setExpenseOpen(false) }} onSave={handleCreateExpense} />
      {toast && <Toast message={toast.message} type={toast.type} onClose={function () { setToast(null) }} />}
    </div>
  )
}

function Sidebar({ activePage, onNavigate, open, onClose, onVault }) {
  return <>
    <div className={'sidebar-scrim ' + (open ? 'is-visible' : '')} onClick={onClose} aria-hidden="true" />
    <aside className={'sidebar ' + (open ? 'is-open' : '')}>
      <div className="brand-row">
        <button className="brand" onClick={function () { onNavigate('overview') }} aria-label="PayArc home"><span className="brand-mark"><span /><span /><span /></span><span>payarc</span></button>
        <IconButton className="mobile-only" icon="x" label="Close navigation" onClick={onClose} />
      </div>
      <div className="workspace-switcher"><span className="workspace-avatar">P</span><span className="workspace-name">Personal space<small>Private workspace</small></span><Icon name="chevronDown" size={16} /></div>
      <nav className="main-nav" aria-label="Main navigation">
        <p className="nav-caption">Workspace</p>
        {NAV_ITEMS.map(function (item) {
          return <button key={item.id} className={'nav-link ' + (activePage === item.id ? 'active' : '')} onClick={function () { onNavigate(item.id) }}>
            <Icon name={item.icon} size={19} /><span>{item.label}</span>{item.id === 'transactions' && <span className="nav-count">7</span>}
          </button>
        })}
      </nav>
      <div className="sidebar-bottom">
        <div className={'vault-nav ' + (activePage === 'vault' ? 'active' : '')}><button className="nav-link" onClick={onVault}><Icon name="lock" size={18} /><span>Privacy vault</span></button><span className="vault-dot" /></div>
        <button className="nav-link muted-link" onClick={function () { onNavigate('overview') }}><Icon name="help" size={18} /><span>Help center</span></button>
        <div className="sidebar-profile"><Avatar /><span><strong>Adarsh Singh</strong><small>Personal account</small></span><IconButton icon="dots" label="Profile options" /></div>
      </div>
    </aside>
  </>
}

function Topbar({ syncState, syncMessage, onOpenMenu, onOpenAssistant, onAddExpense }) {
  const syncCopy = { connecting: 'Connecting securely', online: 'Live sync', partial: 'Partial sync', preview: 'Private preview' }
  return <header className="topbar">
    <IconButton className="menu-toggle mobile-only" icon="menu" label="Open navigation" onClick={onOpenMenu} />
    <div className="sync-status" title={syncMessage || 'Your data is encrypted in transit'}><StatusDot status={syncState} /><span>{syncCopy[syncState]}</span></div>
    <div className="topbar-actions">
      <button className="assistant-trigger" onClick={onOpenAssistant}><span className="assistant-orb"><Icon name="sparkle" size={15} /></span><span>Ask PayArc</span><kbd>⌘ K</kbd></button>
      <IconButton icon="bell" label="Notifications" />
      <button className="add-expense-button" onClick={onAddExpense}><Icon name="plus" size={17} /><span>Add</span></button>
    </div>
  </header>
}

function PageTitle({ eyebrow, title, description, action }) {
  return <div className="page-title-row"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div>{action}</div>
}

function OverviewPage({ dashboard, transactions, budgets, goals, onAddExpense, onGoTo }) {
  const recent = transactions.slice(0, 5)
  return <>
    <PageTitle eyebrow={(dashboard.user && dashboard.user.greeting ? dashboard.user.greeting : 'Welcome back') + ', ' + (dashboard.user && dashboard.user.name ? dashboard.user.name : 'Adarsh Singh')} title="Your money, in focus." description="September 2026 · A clear view of what matters today." action={<button className="primary-button page-add" onClick={onAddExpense}><Icon name="plus" size={18} />Add transaction</button>} />
    <section className="balance-grid">
      <BalanceCard dashboard={dashboard} />
      <MetricCard label="Income" value={money(dashboard.income)} detail="+8.2% vs last month" icon="arrowUp" tone="green" />
      <MetricCard label="Spent" value={money(dashboard.spent)} detail="60% of monthly income" icon="wallet" tone="orange" />
      <MetricCard label="Saved" value={money(dashboard.saved)} detail={Math.round((dashboard.saved / dashboard.income) * 100) + '% savings rate'} icon="vault" tone="purple" />
    </section>
    <section className="dashboard-mosaic">
      <CashflowCard cashflow={dashboard.cashflow || demoDashboard.cashflow} />
      <InsightCard insight={dashboard.insight || demoDashboard.insight} health={healthScore(dashboard.financialHealth || 82)} />
      <CategoryCard entries={dashboard.categoryBreakdown || categoryBreakdown} />
      <div className="card goals-mini-card"><CardHeader title="Goals, in motion" action={<button className="text-button" onClick={function () { onGoTo('goals') }}>See all <Icon name="arrow" size={15} /></button>} /><div className="mini-goals">{goals.slice(0, 2).map(function (goal) { return <MiniGoal key={goal.id} goal={goal} /> })}</div></div>
      <div className="card recent-transactions-card"><CardHeader title="Latest activity" action={<button className="text-button" onClick={function () { onGoTo('transactions') }}>View all <Icon name="arrow" size={15} /></button>} /><div className="activity-list">{recent.map(function (transaction) { return <ActivityRow key={transaction.id} transaction={transaction} /> })}</div></div>
      <BudgetSnapshot budgets={budgets} onGoTo={function () { onGoTo('budgets') }} />
    </section>
  </>
}

function BalanceCard({ dashboard }) {
  return <article className="balance-card">
    <div className="balance-noise" />
    <div className="balance-topline"><span>Available balance</span><span className="private-chip"><Icon name="lock" size={12} />Private</span></div>
    <div className="balance-value">{money(dashboard.balance)}</div>
    <div className="balance-bottom"><span className="up-chip"><Icon name="trend" size={14} />{dashboard.monthlyChange || 12.4}% this month</span><span className="balance-accounts"><i /><i /><i />3 accounts</span></div>
    <div className="balance-graphic" aria-hidden="true"><span className="orbit orbit-a" /><span className="orbit orbit-b" /><span className="orbit orbit-c" /><span className="glow-ball" /></div>
  </article>
}

function MetricCard({ label, value, detail, icon, tone }) {
  return <article className={'metric-card metric-' + tone}><div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon name={icon} size={17} /></span></div><strong>{value}</strong><small>{detail}</small></article>
}

function CashflowCard({ cashflow }) {
  return <article className="card cashflow-card">
    <CardHeader title="Cash flow" trailing={<span className="period-pill">This month <Icon name="chevronDown" size={14} /></span>} />
    <div className="cashflow-summary"><div><span className="legend-dot income-dot" />Income <strong>₹46,200</strong></div><div><span className="legend-dot expense-dot" />Expenses <strong>₹27,780</strong></div><span className="cashflow-net">+₹18,420 net</span></div>
    <CashflowChart values={cashflow} />
  </article>
}

function CashflowChart({ values }) {
  const width = 600
  const height = 188
  const max = Math.max.apply(null, values.reduce(function (all, item) { return all.concat([item.income, item.spend]) }, []).concat([1]))
  const x = function (index) { return 26 + (index * 91) }
  const y = function (value) { return height - 30 - ((value / max) * 128) }
  const createLine = function (key) { return values.map(function (item, index) { return (index ? 'L ' : 'M ') + x(index) + ' ' + y(item[key]) }).join(' ') }
  const incomeArea = createLine('income') + ' L ' + x(values.length - 1) + ' ' + (height - 30) + ' L ' + x(0) + ' ' + (height - 30) + ' Z'
  return <div className="cashflow-chart" role="img" aria-label="Monthly income and expense chart">
    <svg viewBox={'0 0 ' + width + ' ' + height} preserveAspectRatio="none">
      <defs><linearGradient id="incomeFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#bcf86e" stopOpacity=".25" /><stop offset="100%" stopColor="#bcf86e" stopOpacity="0" /></linearGradient></defs>
      {[38, 70, 102, 134].map(function (position) { return <line key={position} x1="18" y1={position} x2="584" y2={position} className="chart-grid-line" /> })}
      <path d={incomeArea} fill="url(#incomeFill)" /><path d={createLine('income')} className="chart-line chart-income" /><path d={createLine('spend')} className="chart-line chart-spend" />
      {values.map(function (item, index) { return <g key={item.label}><circle cx={x(index)} cy={y(item.income)} r="3.5" className="chart-dot income-circle" /><circle cx={x(index)} cy={y(item.spend)} r="3.5" className="chart-dot spend-circle" /></g> })}
    </svg>
    <div className="chart-labels">{values.map(function (item) { return <span key={item.label}>{item.label}</span> })}</div>
  </div>
}

function InsightCard({ insight, health }) {
  return <article className="card insight-card">
    <div className="insight-glow" />
    <div className="insight-header"><span className="ai-label"><span className="tiny-orb"><Icon name="sparkle" size={13} /></span>PAYARC INTELLIGENCE</span><span className="health-score" title="Financial health score">{health}<small>/100</small></span></div>
    <h2>{insight.title}</h2><p>{insight.body}</p>
    <div className="insight-footer"><button className="light-button">{insight.action} <Icon name="arrow" size={15} /></button><span className="health-label"><Icon name="shield" size={14} />Your financial health is strong</span></div>
  </article>
}

function CategoryCard({ entries }) {
  return <article className="card categories-card">
    <CardHeader title="Where your money went" trailing={<span className="period-pill">August <Icon name="chevronDown" size={14} /></span>} />
    <div className="category-content"><DonutChart entries={entries} /><div className="category-legend">{entries.slice(0, 4).map(function (item) { return <div key={item.name} className="category-legend-row"><span className="legend-dot" style={{ backgroundColor: item.color }} /><span>{item.name}</span><strong>{money(item.amount, true)}</strong></div> })}</div></div>
  </article>
}

function DonutChart({ entries }) {
  let cursor = 0
  const stops = entries.map(function (item) { const start = cursor; cursor += item.value; return item.color + ' ' + start + '% ' + cursor + '%' }).join(', ')
  return <div className="donut" style={{ background: 'conic-gradient(' + stops + ')' }} role="img" aria-label="Spending by category"><div className="donut-center"><span>Total spent</span><strong>₹14.3k</strong><small>in August</small></div></div>
}

function MiniGoal({ goal }) {
  const progress = percent(goal.saved, goal.target)
  return <div className="mini-goal"><span className="goal-emoji">{goal.emoji}</span><div className="mini-goal-content"><div><strong>{goal.name}</strong><span>{progress}%</span></div><div className="progress-track"><i style={{ width: progress + '%', background: goal.color }} /></div><small>{money(goal.saved, true)} of {money(goal.target, true)}</small></div></div>
}

function ActivityRow({ transaction }) {
  const isPositive = transaction.amount > 0
  return <div className="activity-row"><span className={'transaction-icon ' + (transaction.color || 'lime')}><Icon name={transaction.icon || 'wallet'} size={17} /></span><div className="activity-copy"><strong>{transaction.merchant}</strong><span>{transaction.category} · {transaction.date}</span></div><div className={'activity-amount ' + (isPositive ? 'positive' : '')}><strong>{isPositive ? '+' : '−'}{money(Math.abs(transaction.amount))}</strong>{transaction.private && <Icon name="lock" size={12} />}</div></div>
}

function BudgetSnapshot({ budgets, onGoTo }) {
  const spent = budgets.reduce(function (sum, item) { return sum + item.spent }, 0)
  const planned = budgets.reduce(function (sum, item) { return sum + item.limit }, 0)
  return <article className="card budget-snapshot"><CardHeader title="Monthly guardrails" action={<button className="text-button" onClick={onGoTo}>Manage <Icon name="arrow" size={15} /></button>} /><div className="budget-big-number"><strong>{money(spent, true)}</strong><span>of {money(planned, true)} planned</span></div><div className="stacked-progress">{budgets.map(function (item) { return <i key={item.id} style={{ width: ((item.spent / planned) * 100) + '%', background: item.color }} /> })}</div><div className="budget-snapshot-footer"><span><Icon name="check" size={14} />3 categories on track</span><span>{money(planned - spent, true)} remaining</span></div></article>
}

function CardHeader({ title, action, trailing }) {
  return <div className="card-header"><h2>{title}</h2>{action || trailing}</div>
}

function TransactionsPage({ transactions, onAddExpense, onDelete }) {
  const [query, setQuery] = useState('')
  const visible = transactions.filter((item) => [item.merchant, item.category, item.account, item.note].filter(Boolean).join(' ').toLowerCase().includes(query.toLowerCase()))
  return <><PageTitle eyebrow="Ledger" title="Every move, accounted for." description="Search and understand your complete financial timeline." action={<button className="primary-button" onClick={onAddExpense}><Icon name="plus" size={17} />Add transaction</button>} /><section className="card ledger-card"><div className="ledger-toolbar"><label className="search-control"><Icon name="search" size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search your transactions" /></label><button className="secondary-button" onClick={onAddExpense}>New</button></div><div className="ledger-summary"><span>{visible.length} transactions</span><span><Icon name="lock" size={14} />Private items remain local</span></div><div className="transaction-table"><div className="transaction-table-head"><span>Transaction</span><span>Account</span><span>When</span><span>Amount</span></div>{visible.map((item) => { const income = item.amount > 0; return <div className="transaction-row" key={item.id}><span className="transaction-main"><span className="transaction-icon"><Icon name={item.icon || 'wallet'} size={18} /></span><span><strong>{item.merchant || item.title}</strong><small>{item.category}{item.note ? ' · ' + item.note : ''}</small></span></span><span className="table-account">{item.account || 'Cash'}</span><span className="table-date">{readableDate(item.date, 'Today')}</span><span className={'table-amount ' + (income ? 'positive' : '')}>{income ? '+' : '−'}{money(Math.abs(item.amount))}</span><button className="delete-transaction" onClick={() => onDelete(item.id)} aria-label={`Delete ${item.merchant || item.title}`} title="Delete transaction"><Icon name="trash" size={16} /></button></div> })}{!visible.length && <div className="empty-state"><Icon name="search" size={25} /><strong>No transactions found</strong></div>}</div></section></>
}

function BudgetsPageLegacy({ budgets, onAddExpense }) {
  const spent = budgets.reduce((sum, item) => sum + Number(item.spent || 0), 0); const limit = budgets.reduce((sum, item) => sum + Number(item.limit || 0), 0)
  return <><PageTitle eyebrow="Spending plan" title="Guardrails that flex with life." description="Keep important categories in a comfortable range." action={<button className="primary-button" onClick={onAddExpense}>Log spending</button>} /><section className="card budget-hero"><div><span className="eyebrow">MONTHLY PLAN</span><strong>{money(spent, true)} <small>of {money(limit, true)}</small></strong><p>{money(Math.max(limit - spent, 0), true)} remains across active budgets.</p></div><div className="budget-hero-gauge"><span>{percent(spent, limit)}%</span></div></section><section className="budget-grid">{budgets.map((item) => { const usage = percent(item.spent, item.limit); return <article className="card budget-detail-card" key={item.id}><div className="budget-detail-head"><span className="category-medallion" style={{ color: item.color }}><Icon name={item.icon || 'wallet'} size={18} /></span><span><strong>{item.category}</strong><small>{item.period || 'Monthly'} budget</small></span><span className={'budget-status ' + (usage >= 80 ? 'watch' : 'good')}>{usage >= 80 ? 'Watch' : 'On track'}</span></div><div className="budget-value-row"><strong>{money(item.spent)}</strong><span>of {money(item.limit)}</span></div><div className="progress-track large"><i style={{ width: usage + '%', background: item.color }} /></div><div className="budget-footer"><span>{money(Math.max(item.limit - item.spent, 0))} left</span><strong>{usage}% used</strong></div></article> })}</section></>
}

function GoalsPageLegacy({ goals, notify }) { return <><PageTitle eyebrow="Future you" title="Make every plan feel possible." description="Small choices become visible progress." action={<button className="primary-button" onClick={() => notify('Goal creation is available through the PayArc API.', 'neutral')}>New goal</button>} /><section className="goals-grid">{goals.map((goal) => { const progress = percent(goal.saved, goal.target); return <article className="card goal-card" key={goal.id}><div className="goal-card-art" style={{ '--goal-color': goal.color }}><span>{goal.emoji || '✦'}</span><i /><i /></div><div className="goal-card-body"><div className="goal-name-row"><span><h2>{goal.name}</h2><p>Target {goal.date || 'when ready'}</p></span><button className="ghost-icon" onClick={() => notify('Contribution flow is ready through the PayArc API.')}><Icon name="plus" size={17} /></button></div><div className="goal-amount"><strong>{money(goal.saved, true)}</strong><span>of {money(goal.target, true)}</span></div><div className="progress-track large"><i style={{ width: progress + '%', background: goal.color }} /></div><div className="goal-foot"><span>{progress}% complete</span><span>{money(Math.max(goal.target - goal.saved, 0), true)} to go</span></div></div></article> })}</section></> }

function BillsPage({ bills, onToggle }) { const total = bills.filter((bill) => bill.active).reduce((sum, bill) => sum + Number(bill.amount || 0), 0); return <><PageTitle eyebrow="Autopilot" title="Your recurring life, simplified." description="Stay ahead of subscriptions and upcoming commitments." /><section className="card bill-overview"><div><span className="eyebrow">ACTIVE MONTHLY COMMITMENTS</span><strong>{money(total)}</strong><p>{bills.filter((bill) => bill.active).length} active plans are watched for you.</p></div><div className="bill-orbit"><span><Icon name="repeat" size={25} /></span><i /><i /></div></section><section className="card bills-list">{bills.map((bill) => <div className="bill-row" key={bill.id}><span className="bill-icon"><Icon name={bill.icon || 'repeat'} size={18} /></span><span className="bill-copy"><strong>{bill.name}</strong><small>{bill.category} · {bill.cadence || 'Monthly'}</small></span><span className="bill-due"><small>Next due</small><strong>{readableDate(bill.due, 'Not set')}</strong></span><strong className="bill-amount">{money(bill.amount)}</strong><button className={'switch ' + (bill.active ? 'on' : '')} onClick={() => onToggle(bill.id)}><i /></button></div>)}</section></> }

function PrivacyVaultPage({ notify }) { return <><PageTitle eyebrow="Privacy vault" title="Your money story stays yours." description="Private by default, clear by design." action={<button className="secondary-button" onClick={() => notify('Your data remains in the local PayArc database.')}>Local storage</button>} /><section className="vault-hero"><div className="vault-seal"><Icon name="lock" size={36} /></div><span className="eyebrow">LOCAL-FIRST PROTECTION</span><h2>Private by default.</h2><p>Your ledger, budgets, goals and coach conversations are stored in PayArc. The included coach does not call an external AI provider.</p><div className="vault-hero-chips"><span><Icon name="shield" size={14} />Private workspace</span><span><Icon name="key" size={14} />Local data control</span><span><Icon name="check" size={14} />No AI API key</span></div></section><section className="privacy-grid">{[['lock','Private transaction notes'],['cloud','You choose the backup'],['sparkle','Explainable coaching']].map((item) => <article className="card privacy-card" key={item[1]}><Icon name={item[0]} size={21} /><h2>{item[1]}</h2><p>PayArc gives you clear controls and keeps your financial information in the scope you choose.</p><button className="text-button" onClick={() => notify('This privacy setting is active in your local workspace.')}>Learn more <Icon name="arrow" size={14} /></button></article>)}</section></> }

function AssistantDrawer({ open, onClose, dashboard, transactions, onAddExpense }) { const [messages, setMessages] = useState(INITIAL_ASSISTANT_MESSAGES); const [draft, setDraft] = useState(''); const [thinking, setThinking] = useState(false); async function send(event, suggestion) { if (event) event.preventDefault(); const text = (suggestion || draft).trim(); if (!text || thinking) return; setMessages((items) => items.concat({ id: Date.now(), role: 'user', text })); setDraft(''); setThinking(true); try { const reply = await payarcApi.askAssistant(text, { balance: dashboard.balance, transactions: transactions.length }); setMessages((items) => items.concat({ id: Date.now() + 1, role: 'assistant', text: reply.response || reply.message || 'I could not create that insight.', suggestions: reply.suggestions || [] })) } catch { setMessages((items) => items.concat({ id: Date.now() + 1, role: 'assistant', text: 'Start the PayArc API to unlock live private analysis.', suggestions: ['How can I save more?'] })) } finally { setThinking(false) } } return <aside className={'assistant-drawer ' + (open ? 'is-open' : '')}><div className="assistant-drawer-head"><div><span className="assistant-orb"><Icon name="sparkle" size={15} /></span><span><strong>PayArc Coach</strong><small>Private financial guidance</small></span></div><IconButton icon="x" label="Close assistant" onClick={onClose} /></div><div className="assistant-privacy"><Icon name="lock" size={14} />Your conversation stays private.</div><div className="assistant-messages">{messages.map((message) => <div className={'chat-bubble ' + message.role} key={message.id}><p>{message.text}</p>{message.suggestions && <div className="suggestion-list">{message.suggestions.map((suggestion) => <button key={suggestion} onClick={() => send(null, suggestion)}>{suggestion}<Icon name="arrow" size={13} /></button>)}</div>}</div>)}{thinking && <div className="chat-bubble assistant thinking"><span /><span /><span /></div>}</div><div className="assistant-quick-action"><button onClick={onAddExpense}>Capture a transaction</button></div><form className="assistant-composer" onSubmit={send}><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about your money..." /><button aria-label="Send"><Icon name="send" size={17} /></button></form></aside> }

function QuickExpenseModal({ open, onClose, onSave }) { const [form, setForm] = useState({ kind: 'expense', amount: '', merchant: '', category: 'Groceries', account: accounts[0], note: '', private: true, receipt: null }); if (!open) return null; const update = (key, value) => setForm((item) => ({ ...item, [key]: value })); function submit(event) { event.preventDefault(); if (Number(form.amount) > 0) { onSave(form); setForm({ kind: 'expense', amount: '', merchant: '', category: 'Groceries', account: accounts[0], note: '', private: true, receipt: null }) } } return <div className="modal-scrim"><section className="quick-modal" role="dialog" aria-modal="true"><div className="modal-head"><div><span className="eyebrow">QUICK CAPTURE</span><h2>Add a transaction</h2></div><IconButton icon="x" label="Close" onClick={onClose} /></div><form onSubmit={submit}><div className="segmented-control"><button type="button" className={form.kind === 'expense' ? 'selected' : ''} onClick={() => update('kind', 'expense')}>Expense</button><button type="button" className={form.kind === 'income' ? 'selected' : ''} onClick={() => update('kind', 'income')}>Income</button></div><label className="amount-input"><span>Amount</span><div><b>₹</b><input autoFocus type="number" min="1" value={form.amount} onChange={(event) => update('amount', event.target.value)} placeholder="0" /></div></label><div className="form-grid"><label>Merchant<input value={form.merchant} onChange={(event) => update('merchant', event.target.value)} placeholder="e.g. Groceries" /></label><label>Category<select value={form.category} onChange={(event) => update('category', event.target.value)}>{categories.map((item) => <option key={item}>{item}</option>)}</select></label><label>Account<select value={form.account} onChange={(event) => update('account', event.target.value)}>{accounts.map((item) => <option key={item}>{item}</option>)}</select></label><label className="wide">Private note<textarea value={form.note} onChange={(event) => update('note', event.target.value)} placeholder="Optional context" /></label><label className="wide">Receipt image / screenshot<input type="file" accept="image/png,image/jpeg,image/webp,application/pdf" onChange={(event) => update('receipt', event.target.files?.[0] || null)} /></label></div><label className="privacy-toggle"><input type="checkbox" checked={form.private} onChange={(event) => update('private', event.target.checked)} /><span><Icon name="lock" size={15} /></span><span><strong>Keep this private</strong><small>Only visible in your personal workspace</small></span></label><div className="modal-actions"><button type="button" className="text-button" onClick={onClose}>Cancel</button><button className="primary-button">Save transaction</button></div></form></section></div> }

function Toast({ message, type, onClose }) { return <div className={'toast toast-' + type} role="status"><Icon name={type === 'success' ? 'check' : 'sparkle'} size={16} /><p>{message}</p><IconButton icon="x" label="Dismiss" onClick={onClose} /></div> }
function DashboardSkeleton() { return <section className="page-wrap skeleton-page"><div className="skeleton skeleton-title" /><div className="skeleton-balance-grid"><div className="skeleton skeleton-balance" /><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div><div className="skeleton skeleton-large" /></section> }

export default App
function ToolsPage({ notify }) {
  const [profiles, setProfiles] = useState([]); const [alerts, setAlerts] = useState([]); const [status, setStatus] = useState(null); const [busy, setBusy] = useState(false); const [profileName, setProfileName] = useState(''); const importRef = useRef(null)
  const refresh = async () => { try { const [p, a, s] = await Promise.all([payarcApi.getProfiles(), payarcApi.getAnomalies(), payarcApi.getCopilotStatus()]); setProfiles(p); setAlerts(a.alerts || []); setStatus(s) } catch { notify('Could not refresh tools while the API is offline.', 'neutral') } }
  useEffect(() => { refresh() }, [])
  const withBusy = async (action) => { setBusy(true); try { await action() } catch (error) { notify(error.message || 'Action failed', 'neutral') } finally { setBusy(false) } }
  return <><PageTitle eyebrow="Control center" title="Your data, your way." description="Import records, protect backups, use reports, switch profiles, and keep an eye on unusual spending." />
    <section className="tools-grid">
      <article className="card tool-card"><span className="tool-icon"><Icon name="upload" size={20} /></span><h2>Import transactions</h2><p>Bring in CSV or Excel statements. Categories and accounts are mapped automatically.</p><input ref={importRef} className="visually-hidden" type="file" accept=".csv,.xlsx" onChange={(event) => { const file = event.target.files?.[0]; if (file) withBusy(async () => { const result = await payarcApi.importTransactions(file); notify(`${result.imported} transactions imported`); event.target.value = '' }) }} /><button className="secondary-button" disabled={busy} onClick={() => importRef.current?.click()}>Choose CSV / Excel</button></article>
      <article className="card tool-card"><span className="tool-icon"><Icon name="file" size={20} /></span><h2>Reports & exports</h2><p>Download a presentation-ready PDF report or a portable CSV copy of your ledger.</p><div className="tool-actions"><a className="secondary-button" href={payarcApi.downloadReport()} target="_blank" rel="noreferrer">PDF report</a><a className="secondary-button" href={payarcApi.downloadCsv()}>CSV export</a></div></article>
      <article className="card tool-card"><span className="tool-icon"><Icon name="cloud" size={20} /></span><h2>Private backup</h2><p>Create an on-device database snapshot before making large changes or importing data.</p><button className="secondary-button" disabled={busy} onClick={() => withBusy(async () => { const backup = await payarcApi.createBackup(); notify(`Backup created: ${backup.backup}`) })}>Create backup</button></article>
      <article className="card tool-card"><span className="tool-icon"><Icon name="sparkle" size={20} /></span><h2>PayArc Copilot</h2><p>{status?.configured ? (status.last_error ? `Gemini needs attention: ${status.last_error}` : `Gemini ${status.model} is configured. Copilot receives only an aggregate summary.`) : 'Private local Copilot is active. Add GEMINI_API_KEY to your local .env to enable Gemini.'}</p><div className="tool-actions"><span className={'provider-badge ' + (status?.configured && !status.last_error ? 'connected' : '')}>{status?.configured && !status?.last_error ? 'Gemini configured' : 'Local Copilot'}</span><button className="secondary-button" disabled={busy || !status?.configured} onClick={() => withBusy(async () => { const checked = await payarcApi.verifyCopilot(); setStatus(checked); notify(checked.message, checked.reachable ? 'success' : 'neutral') })}>Test Gemini</button></div></article>
    </section>
    <section className="tools-lower"><article className="card data-panel"><CardHeader title="Profiles" /><div className="profile-list">{profiles.map((profile) => <button key={profile.id} className={'profile-row ' + (profile.is_active ? 'active' : '')} onClick={() => withBusy(async () => { await payarcApi.activateProfile(profile.id); await refresh(); notify(`${profile.name} is now active`) })}><span className="profile-dot" style={{ background: profile.color }} /><span><strong>{profile.name}</strong><small>{profile.is_active ? 'Active profile' : 'Switch workspace'}</small></span>{profile.is_active && <Icon name="check" size={16} />}</button>)}</div><form className="profile-create" onSubmit={(event) => { event.preventDefault(); if (profileName.trim()) withBusy(async () => { await payarcApi.createProfile({ name: profileName }); setProfileName(''); await refresh(); notify('Profile created') }) }}><input value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="New profile name" /><button className="primary-button" disabled={busy}>Add profile</button></form></article><article className="card data-panel"><CardHeader title="Smart alerts" /><p className="panel-copy">Transparent checks flag transactions above 2.5× your normal category spend.</p>{alerts.length ? <div className="alert-list">{alerts.map((alert) => <div className="alert-row" key={alert.transaction_id}><Icon name="trend" size={16} /><span><strong>{alert.merchant}</strong><small>{alert.message}</small></span><b>{money(alert.amount)}</b></div>)}</div> : <div className="empty-inline"><Icon name="check" size={17} />No unusual spending patterns found.</div>}</article></section>
  </>
}
function BudgetsPage({ budgets, onAddExpense, onRefresh, notify }) {
  const [form, setForm] = useState({ category: 'Groceries', limit: '', alert: '80' }); const [saving, setSaving] = useState(false)
  const spent = budgets.reduce((sum, item) => sum + Number(item.spent || 0), 0); const limit = budgets.reduce((sum, item) => sum + Number(item.limit || 0), 0)
  async function createBudget(event) { event.preventDefault(); if (Number(form.limit) <= 0) return; setSaving(true); try { await payarcApi.createMonthlyBudget({ category: form.category, limit: Number(form.limit), alert_percentage: Number(form.alert) }); await onRefresh(); setForm({ ...form, limit: '' }); notify(`Monthly ${form.category} budget created`) } catch (error) { notify(error.message || 'Could not create budget', 'neutral') } finally { setSaving(false) } }
  return <><PageTitle eyebrow="Spending plan" title="Guardrails that flex with life." description="Set monthly limits, choose warnings, and see exactly what remains." action={<button className="primary-button" onClick={onAddExpense}>Log spending</button>} /><section className="card budget-hero"><div><span className="eyebrow">THIS MONTH</span><strong>{money(spent, true)} <small>of {money(limit, true)}</small></strong><p>{money(Math.max(limit - spent, 0), true)} remains before your planned caps.</p></div><div className="budget-hero-gauge"><span>{percent(spent, limit)}%</span></div></section><section className="card budget-create-card"><div><h2>Set a monthly budget</h2><p>Create a category limit with a reminder threshold. It recalculates whenever you add or delete a transaction.</p></div><form onSubmit={createBudget}><select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{categories.map((category) => <option key={category}>{category}</option>)}</select><input type="number" min="1" value={form.limit} onChange={(event) => setForm({ ...form, limit: event.target.value })} placeholder="Monthly limit" /><select value={form.alert} onChange={(event) => setForm({ ...form, alert: event.target.value })}><option value="70">Alert at 70%</option><option value="80">Alert at 80%</option><option value="90">Alert at 90%</option></select><button className="primary-button" disabled={saving}>{saving ? 'Saving…' : 'Create budget'}</button></form></section><section className="budget-grid">{budgets.map((item) => { const usage = percent(item.spent, item.limit); return <article className="card budget-detail-card" key={item.id}><div className="budget-detail-head"><span className="category-medallion" style={{ color: item.color }}><Icon name={item.icon || 'wallet'} size={18} /></span><span><strong>{item.category}</strong><small>Monthly · Alert at {item.alert_percentage || 80}%</small></span><span className={'budget-status ' + (usage >= (item.alert_percentage || 80) ? 'watch' : 'good')}>{usage >= (item.alert_percentage || 80) ? 'Alert' : 'On track'}</span></div><div className="budget-value-row"><strong>{money(item.spent)}</strong><span>of {money(item.limit)}</span></div><div className="progress-track large"><i style={{ width: usage + '%', background: item.color }} /></div><div className="budget-footer"><span>{money(Math.max(item.limit - item.spent, 0))} left</span><strong>{usage}% used</strong></div></article> })}</section></>
}

function GoalsPage({ goals, notify, onRefresh }) {
  const [selected, setSelected] = useState(null); const [amount, setAmount] = useState(''); const [newGoal, setNewGoal] = useState(false); const [goalForm, setGoalForm] = useState({ name: '', target: '', monthly: '' }); const [saving, setSaving] = useState(false)
  async function contribute(event) { event.preventDefault(); if (!selected || Number(amount) <= 0) return; setSaving(true); try { await payarcApi.contributeToGoal(selected.id, Number(amount)); await onRefresh(); notify(`${money(Number(amount))} added to ${selected.name}`); setSelected(null); setAmount('') } catch (error) { notify(error.message || 'Could not add money', 'neutral') } finally { setSaving(false) } }
  async function createGoal(event) { event.preventDefault(); if (!goalForm.name || Number(goalForm.target) <= 0) return; setSaving(true); try { await payarcApi.createGoal({ name: goalForm.name, target_amount: Number(goalForm.target), current_amount: 0, target_date: null, notes: goalForm.monthly ? `Suggested monthly saving: ${goalForm.monthly}` : null }); await onRefresh(); notify('New savings goal created'); setNewGoal(false); setGoalForm({ name: '', target: '', monthly: '' }) } catch (error) { notify(error.message || 'Could not create goal', 'neutral') } finally { setSaving(false) } }
  return <><PageTitle eyebrow="Future you" title="Make every plan feel possible." description="Add money whenever you save and watch the finish line move closer." action={<button className="primary-button" onClick={() => setNewGoal(true)}>New goal</button>} /><section className="goals-grid">{goals.map((goal) => { const progress = percent(goal.saved, goal.target); return <article className="card goal-card" key={goal.id}><div className="goal-card-art" style={{ '--goal-color': goal.color }}><span>{goal.emoji || '✦'}</span><i /><i /></div><div className="goal-card-body"><div className="goal-name-row"><span><h2>{goal.name}</h2><p>Target {goal.date || 'when ready'}</p></span><button className="ghost-icon" onClick={() => setSelected(goal)} aria-label={'Add money to ' + goal.name}><Icon name="plus" size={17} /></button></div><div className="goal-amount"><strong>{money(goal.saved, true)}</strong><span>of {money(goal.target, true)}</span></div><div className="progress-track large"><i style={{ width: progress + '%', background: goal.color }} /></div><div className="goal-foot"><span>{progress}% complete</span><span>{money(Math.max(goal.target - goal.saved, 0), true)} to go</span></div><button className="goal-add-button" onClick={() => setSelected(goal)}>+ Add money</button></div></article> })}</section>{selected && <div className="inline-dialog-scrim"><form className="inline-dialog" onSubmit={contribute}><button type="button" className="modal-close" onClick={() => setSelected(null)}><Icon name="x" size={17} /></button><span className="eyebrow">GOAL CONTRIBUTION</span><h2>Add money to {selected.name}</h2><p>Current progress: {money(selected.saved)} of {money(selected.target)}</p><label>Amount<input autoFocus type="number" min="1" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0" /></label><button className="primary-button" disabled={saving}>{saving ? 'Adding…' : 'Add to goal'}</button></form></div>}{newGoal && <div className="inline-dialog-scrim"><form className="inline-dialog" onSubmit={createGoal}><button type="button" className="modal-close" onClick={() => setNewGoal(false)}><Icon name="x" size={17} /></button><span className="eyebrow">NEW SAVINGS GOAL</span><h2>Create a goal</h2><label>Name<input value={goalForm.name} onChange={(event) => setGoalForm({ ...goalForm, name: event.target.value })} placeholder="e.g. Emergency fund" /></label><label>Target amount<input type="number" min="1" value={goalForm.target} onChange={(event) => setGoalForm({ ...goalForm, target: event.target.value })} placeholder="0" /></label><label>Monthly saving target <small>(optional)</small><input type="number" min="1" value={goalForm.monthly} onChange={(event) => setGoalForm({ ...goalForm, monthly: event.target.value })} placeholder="0" /></label><button className="primary-button" disabled={saving}>{saving ? 'Creating…' : 'Create goal'}</button></form></div>}</>
}
