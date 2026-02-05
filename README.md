# Expense Tracker with ML Forecasting

A full-stack web application for tracking personal expenses with machine learning-powered spending predictions.

## Features

- **Expense Management**: Add, view, and delete transactions with categorization
- **Smart Analytics**: Real-time statistics and spending insights
- **ML Forecasting**: Predict future expenses using Holt-Winters Exponential Smoothing
- **Data Visualization**: Interactive charts powered by Chart.js
- **Excel Export**: Download detailed expense reports with summary sheets
- **Mock Data Generator**: Create realistic test data with trend and seasonality patterns

## Preview
![photo_2026-02-05_05-39-33](https://github.com/user-attachments/assets/b37592d1-a39d-4a43-b368-6411d4404aff)
## Live demo
[**SITE**](https://hdmi.pythonanywhere.com/)
## Tech Stack

**Backend:**
- Flask (REST API)
- pandas (data processing)
- statsmodels (time series forecasting)
- NumPy (numerical operations)

**Frontend:**
- Vanilla JavaScript
- Chart.js (interactive charts)
- HTML5/CSS3

**Data Storage:**
- CSV (with validation and type enforcement)

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. **Clone the repository:**
```bash
git clone [https://github.com/NSHDMI/Expense-Tracker.git](https://github.com/NSHDMI/Expense-Tracker.git)
cd Expense-Tracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open browser at `http://127.0.0.1:5000`

## API Documentation

### Expenses

**GET** `/api/expenses`
- Returns all expenses
- Response: `[{date, category, amount, description}, ...]`

**POST** `/api/expenses`
- Add new expense
- Body: `{date: "YYYY-MM-DD", category: string, amount: number, description?: string}`
- Validates: date format, positive amount, valid category

**DELETE** `/api/expenses/<index>`
- Delete expense by index
- Returns: `{status: "deleted"}`

### Statistics

**GET** `/api/stats`
- Returns: `{total, average, count, top_category}`

### Forecasting

**GET** `/api/forecast`
- Generates 4-week spending forecast using Holt-Winters model
- Requires: minimum 8 weeks of historical data
- Returns: `{total_forecast, pie, timeline, model, data_points_used}`

### Data Management

**POST** `/api/generate`
- Generate 500 mock records with realistic patterns
- Features: 0.05% daily growth trend, 2x weekend spending on Food & Entertainment

**DELETE** `/api/expenses/clear`
- Clear all data (requires `{confirm: true}` in body)

**GET** `/api/export`
- Download Excel file with 3 sheets: Expenses, Summary, By Category

**GET** `/api/categories`
- Returns list of valid expense categories

## Machine Learning Model

### Holt-Winters Exponential Smoothing

The forecasting engine uses triple exponential smoothing to capture:

- **Trend**: Long-term increase/decrease in spending
- **Seasonality**: Weekly patterns (e.g., higher weekend spending)
- **Level**: Base spending amount

**Model Parameters:**
- Aggregation: Weekly (more stable than daily)
- Seasonal periods: 4 weeks (monthly cycle)
- Forecast horizon: 4 weeks
- Minimum data: 8 weeks

**Data Preprocessing:**
- Zero-day filling with 7-day rolling mean
- Outlier handling via coercion
- Date validation and sorting

## Project Structure

```
Expense-Tracker/
├── app.py              # Flask server + ML Logic
├── requirements.txt    # Python dependencies
├── expenses.csv        # Local data storage
├── static/
│   ├── script.js       # API handling & UI logic
│   └── style.css       # Modern UI & Dark Mode
└── templates/
    └── index.html      # Main application interface
```

### Data Quality Requirements for Forecasting

- Minimum 8 weeks of transaction history
- Less than 50% zero-spending weeks
- Consistent data entry (no large gaps)

## Known Limitations

- Single-user application (no authentication)
- CSV storage (not suitable for production scale)
- Forecast accuracy depends on data quality and consistency

## Future Enhancements

- [ ] User authentication and multi-user support
- [ ] Database migration (PostgreSQL/SQLite)
- [ ] Budget tracking and alerts
- [ ] Recurring expense detection
- [ ] Mobile-responsive UI improvements
- [ ] PDF report generation
- [ ] Category customization

## License

MIT
