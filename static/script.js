let categoryChart = null;
let timelineChart = null;

document.getElementById('date').valueAsDate = new Date();

window.addEventListener('load', updateAllData);

function updateAllData() {
    loadStats();
    loadExpenses();
    loadCharts();
    loadForecast();
}

document.getElementById('expense-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const data = {
        date: document.getElementById('date').value,
        category: document.getElementById('category').value,
        amount: document.getElementById('amount').value,
        description: document.getElementById('description').value
    };

    const response = await fetch('/api/expenses', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    if (response.ok) {
        document.getElementById('expense-form').reset();
        document.getElementById('date').valueAsDate = new Date();
        updateAllData();
    }
});

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        document.getElementById('total-spent').textContent = `${Number(stats.total).toFixed(2)} EUR`;
        document.getElementById('avg-expense').textContent = `${Number(stats.average).toFixed(2)} EUR`;
        document.getElementById('transaction-count').textContent = stats.count;
        document.getElementById('top-category').textContent = stats.top_category;
    } catch (error) { 
        console.error('Stats Error:', error); 
    }
}

async function loadExpenses() {
    try {
        const response = await fetch('/api/expenses');
        const data = await response.json();
        const tbody = document.getElementById('transactions-body');
        tbody.innerHTML = '';

        const expenses = Array.isArray(data) ? data : data.expenses;

        expenses.slice().reverse().forEach((expense, index) => {
            const actualIndex = expenses.length - 1 - index;
            const amount = Number(expense.amount);
            const amountClass = amount > 100 ? 'text-danger font-bold' : '';
            
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${expense.date}</td>
                <td><span class="category-tag">${expense.category}</span></td>
                <td class="${amountClass}">${amount.toFixed(2)} EUR</td>
                <td>${expense.description || expense.Description || ''}</td>
                <td><button class="delete-btn" onclick="deleteExpense(${actualIndex})">Delete</button></td>
            `;
        });
    } catch (error) { 
        console.error('Expenses Error:', error); 
    }
}

async function deleteExpense(index) {
    if (!confirm('Confirm deletion?')) return;
    await fetch(`/api/expenses/${index}`, {method: 'DELETE'});
    updateAllData();
}

document.getElementById('month-filter').addEventListener('change', loadCharts);

async function loadCharts() {
    try {
        const response = await fetch('/api/expenses');
        const data = await response.json();
        let expenses = Array.isArray(data) ? data : data.expenses;
        
        if (!expenses || expenses.length === 0) {
            if (categoryChart) { categoryChart.destroy(); categoryChart = null; }
            if (timelineChart) { timelineChart.destroy(); timelineChart = null; }
            return;
        }

        const filterDropdown = document.getElementById('month-filter');
        const currentFilter = filterDropdown.value;

        const availableMonths = [...new Set(expenses.map(e => e.date.substring(0, 7)))].sort().reverse();
        
        if (filterDropdown.options.length <= 1) {
            availableMonths.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = new Date(m + "-01").toLocaleString('en-us', {month:'long', year:'numeric'});
                filterDropdown.appendChild(opt);
            });
        }

        if (currentFilter !== 'all') {
            expenses = expenses.filter(e => e.date.startsWith(currentFilter));
        }

        const categories = [...new Set(expenses.map(item => item.category))];
        const categorySums = categories.map(cat => 
            expenses.filter(item => item.category === cat).reduce((s, i) => s + Number(i.amount), 0)
        );

        const sortedData = [...expenses].sort((a, b) => new Date(a.date) - new Date(b.date));
        const dates = [...new Set(sortedData.map(item => item.date))];
        const dailySums = dates.map(date => 
            sortedData.filter(item => item.date === date).reduce((s, i) => s + Number(i.amount), 0)
        );
        
        const ctxCat = document.getElementById('category-chart-canvas').getContext('2d');
        if (categoryChart) {
            categoryChart.data.labels = categories;
            categoryChart.data.datasets[0].data = categorySums;
            categoryChart.update();
        } else {
            categoryChart = new Chart(ctxCat, {
                type: 'pie',
                data: {
                    labels: categories,
                    datasets: [{
                        data: categorySums,
                        backgroundColor: ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#64748B']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        const ctxTime = document.getElementById('timeline-chart-canvas').getContext('2d');
        if (timelineChart) {
            timelineChart.data.labels = dates;
            timelineChart.data.datasets[0].data = dailySums;
            timelineChart.update();
        } else {
            timelineChart = new Chart(ctxTime, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Daily Spending',
                        data: dailySums,
                        borderColor: '#4F46E5',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    } catch (error) { 
        console.error('Charts Error:', error); 
    }
}

async function loadForecast() {
    const amountEl = document.getElementById('forecast-amount');
    const diffEl = document.getElementById('forecast-diff');

    try {
        const response = await fetch('/api/forecast');
        const forecastData = await response.json();
        
        if (forecastData.error) {
            amountEl.textContent = "--- EUR";
            diffEl.textContent = "Analysis: Insufficient data";
            return;
        }

        if (forecastData.total_forecast) {
            amountEl.textContent = `${Number(forecastData.total_forecast).toLocaleString()} EUR`;
            diffEl.textContent = "30-day Forecast (ETS Model)";
        }
    } catch (error) {
        console.error('Forecast Load Error:', error);
    }
}

document.getElementById('generate-btn').addEventListener('click', async () => {
    if (!confirm('Replace all data with 500 random records?')) return;

    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    try {
        const response = await fetch('/api/generate', { method: 'POST' });
        if (response.ok) updateAllData();
    } catch (error) {
        console.error('Generation Error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate Data';
    }
});

document.getElementById('clear-btn').addEventListener('click', async () => {
    if (!confirm('Delete all records permanently?')) return;

    try {
        const response = await fetch('/api/expenses/clear', { 
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ confirm: true }) 
        });

        if (response.ok) {
            updateAllData();
        } else {
            const errorData = await response.json();
            alert('Error: ' + errorData.error);
        }
    } catch (error) {
        console.error('Clear Error:', error);
    }
});

document.getElementById('export-btn').addEventListener('click', () => {
    window.location.href = '/api/export';
});