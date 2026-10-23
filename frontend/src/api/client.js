const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status) { super(message); this.name = 'ApiError'; this.status = status }
}

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 6500)
  try {
    const response = await fetch(`${API_URL}${path}`, { headers: { 'Content-Type': 'application/json', ...options.headers }, signal: controller.signal, ...options })
    const body = await response.json().catch(() => null)
    if (!response.ok) throw new ApiError(body?.detail || body?.message || 'Something went wrong', response.status)
    return body
  } finally { window.clearTimeout(timeout) }
}

async function upload(path, formData) {
  const response = await fetch(`${API_URL}${path}`, { method: 'POST', body: formData })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(body?.detail || 'Upload failed', response.status)
  return body
}

export const payarcApi = {
  getDashboard: () => request('/dashboard'), getTransactions: () => request('/transactions'),
  createTransaction: (data) => request('/transactions', { method: 'POST', body: JSON.stringify(data) }),
  deleteTransaction: (id) => request(`/transactions/${id}`, { method: 'DELETE' }),
  getBudgets: () => request('/budgets'), getGoals: () => request('/goals'), getBills: () => request('/recurring-bills'),
  getCategories: () => request('/categories'),
  createGoal: (data) => request('/goals', { method: 'POST', body: JSON.stringify(data) }),
  contributeToGoal: (id, amount) => request(/goals//contributions, { method: 'POST', body: JSON.stringify({ amount }) }),
  createMonthlyBudget: (data) => request('/budgets/quick', { method: 'POST', body: JSON.stringify(data) }),
  updateBill: (id, data) => request(`/recurring-bills/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  askAssistant: (message, context) => request('/assistant/chat', { method: 'POST', body: JSON.stringify({ message, context }) }),
  getProfiles: () => request('/profiles'), createProfile: (data) => request('/profiles', { method: 'POST', body: JSON.stringify(data) }),
  activateProfile: (id) => request(`/profiles/${id}/activate`, { method: 'POST' }),
  importTransactions: (file) => { const form = new FormData(); form.append('file', file); return upload('/imports/transactions', form) },
  downloadReport: () => `${API_URL}/reports/transactions.pdf`, createBackup: () => request('/backups/create', { method: 'POST' }), getBackups: () => request('/backups'),
  uploadReceipt: (expenseId, file) => { const form = new FormData(); form.append('expense_id', expenseId); form.append('file', file); return upload('/receipts', form) },
  getCopilotStatus: () => request('/assistant/status'),
  verifyCopilot: () => request('/assistant/verify', { method: 'POST' }),
  getAnomalies: () => request('/insights/anomalies'),
  downloadCsv: () => API_URL + '/exports/transactions.csv',
}
export const apiBaseUrl = API_URL
