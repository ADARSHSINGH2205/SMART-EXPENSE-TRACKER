const dialog = document.getElementById('expenseDialog');
const form = document.getElementById('expenseForm');
document.getElementById('openExpense').addEventListener('click', () => {
  form.date.value = new Date().toISOString().slice(0, 10);
  dialog.showModal();
});
form.addEventListener('submit', (event) => {
  if (event.submitter.value === 'cancel') return;
  event.preventDefault();
  const data = new FormData(form);
  const amount = Number(data.get('amount')).toLocaleString('en-IN');
  const category = data.get('category');
  const title = data.get('merchant') || category;
  const item = document.createElement('div');
  item.className = 'transaction';
  item.innerHTML = `<div class="trans-icon shop">▣</div><div class="trans-name"><b>${escapeHtml(title)}</b><small>Today · ${escapeHtml(category)}</small></div><span class="tag personal">${data.get('privacy') === 'Personal' ? 'Personal' : 'Shared'}</span><b class="amount">− ₹${amount}</b>`;
  document.getElementById('transactionList').prepend(item);
  dialog.close();
  form.reset();
});
function escapeHtml(value) { const el = document.createElement('div'); el.textContent = value; return el.innerHTML; }
