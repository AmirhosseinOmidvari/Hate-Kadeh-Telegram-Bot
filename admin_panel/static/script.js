const API_BASE = '';

function showMessage(msg, isError = false) {
    const host = document.getElementById('toastHost') || document.body;
    const toast = document.createElement('div');
    toast.className = `toast ${isError ? 'error' : 'success'}`;
    toast.textContent = msg;
    host.appendChild(toast);
    setTimeout(() => toast.remove(), 2800);
}

function _csrfHeaders() {
    return window.CSRF_TOKEN ? { 'X-CSRF-Token': window.CSRF_TOKEN } : {};
}

function _postOptions() {
    return {
        method: 'POST',
        credentials: 'same-origin',
        headers: _csrfHeaders()
    };
}

async function approveMessage(id, element) {
    if (!confirm('آیا از تایید این پیام مطمئنی؟')) return;
    try {
        const res = await fetch(`${API_BASE}/approve/${id}`, _postOptions());
        const data = await res.json().catch(() => ({}));
        if (data.status === 'ok') {
            showMessage(`✅ پیام ${id} تایید شد`);
            if (element) {
                const row = element.closest('tr');
                if (row) row.remove();
            } else {
                location.reload();
            }
        } else {
            showMessage(data.error || '❌ خطا در تایید', true);
        }
    } catch (err) {
        showMessage('❌ خطای شبکه', true);
    }
}

async function rejectMessage(id, element) {
    if (!confirm('آیا از حذف این پیام اطمینان دارید؟')) return;
    try {
        const res = await fetch(`${API_BASE}/reject/${id}`, _postOptions());
        const data = await res.json().catch(() => ({}));
        if (data.status === 'ok') {
            showMessage(`🗑 پیام ${id} حذف شد`);
            if (element) {
                const row = element.closest('tr');
                if (row) row.remove();
            } else {
                location.reload();
            }
        } else {
            showMessage(data.error || '❌ خطا در حذف', true);
        }
    } catch (err) {
        showMessage('❌ خطای شبکه', true);
    }
}

function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const filter = input.value.toLowerCase();
    const rows = document.querySelectorAll(`#${tableId} tbody tr`);
    rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
}

async function refreshStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`, { credentials: 'same-origin' });
        const stats = await res.json().catch(() => null);
        if (!stats) return;
        document.querySelectorAll('.stat-number').forEach(el => {
            const key = el.getAttribute('data-stat');
            if (key && stats[key] !== undefined) el.innerText = stats[key];
        });
    } catch (e) {}
}

async function approveReply(id) {
    if (!confirm('آیا از تایید این پاسخ مطمئنی؟')) return;
    try {
        const res = await fetch(`${API_BASE}/reply/approve/${id}`, _postOptions());
        const data = await res.json().catch(() => ({}));
        if (data.status === 'ok') {
            showMessage(`✅ پاسخ ${id} تایید شد`);
            location.reload();
        } else {
            showMessage(data.error || '❌ خطا در تایید پاسخ', true);
        }
    } catch(e) {}
}

async function rejectReply(id) {
    if (!confirm('آیا از حذف این پاسخ اطمینان دارید؟')) return;
    try {
        const res = await fetch(`${API_BASE}/reply/reject/${id}`, _postOptions());
        const data = await res.json().catch(() => ({}));
        if (data.status === 'ok') {
            showMessage(`🗑 پاسخ ${id} حذف شد`);
            location.reload();
        } else {
            showMessage(data.error || '❌ خطا در حذف پاسخ', true);
        }
    } catch (err) {
        showMessage('❌ خطای شبکه', true);
    }
}

if (window.location.pathname.includes('/dashboard')) {
    setInterval(refreshStats, 30000);
}