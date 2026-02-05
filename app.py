import os
import pandas as pd
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, send_file
import io
import numpy as np

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    FORECAST_AVAILABLE = True
except ImportError:
    print("WARNING: statsmodels not installed. Forecasting will not be available.")
    print("Install: pip install statsmodels")
    FORECAST_AVAILABLE = False

try:
    import openpyxl
    EXCEL_EXPORT_AVAILABLE = True
except ImportError:
    print("WARNING: openpyxl not installed. Excel export will not be available.")
    print("Install: pip install openpyxl")
    EXCEL_EXPORT_AVAILABLE = False

app = Flask(__name__)

FILE_NAME = "expenses.csv"
COLUMNS = ["date", "category", "amount", "description"]
VALID_CATEGORIES = ['Food', 'Transport', 'Entertainment', 'Health', 'Bills', 'Shopping', 'Other']

def read_data() -> pd.DataFrame:
    if not os.path.exists(FILE_NAME):
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_csv(FILE_NAME)
        if not set(COLUMNS).issubset(df.columns):
            return pd.DataFrame(columns=COLUMNS)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        return df
    except Exception as e:
        print(f"Error reading data: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_data(df: pd.DataFrame) -> None:
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values(by="date")
    df.to_csv(FILE_NAME, index=False, date_format="%Y-%m-%d")

def prepare_data_for_forecast(method='daily'):
    """
    Args:
        method: 'daily' or 'weekly' aggregation
    
    Returns:
        pd.Series with datetime index
    """
    df = read_data()
    
    if df.empty:
        return pd.Series(dtype=float)
    
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0)
    
    if method == 'weekly':
        df['week'] = df['date'].dt.to_period('W')
        weekly_expense = df.groupby('week')['amount'].sum()
        weekly_expense.index = weekly_expense.index.to_timestamp()
        return weekly_expense
    
    else:
        daily_expense = df.groupby("date")["amount"].sum()
        
        date_range = pd.date_range(
            start=daily_expense.index.min(),
            end=daily_expense.index.max(),
            freq='D'
        )
        
        daily_expense = daily_expense.reindex(date_range, fill_value=0)
        
        # Replace zeros with rolling mean to avoid breaking Holt-Winters
        daily_expense = daily_expense.replace(0, np.nan)
        rolling_mean = daily_expense.rolling(window=7, min_periods=1, center=True).mean()
        daily_expense = daily_expense.fillna(rolling_mean)
        daily_expense = daily_expense.fillna(daily_expense.mean())
        
        return daily_expense

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    df = read_data()
    
    if not df.empty and 'date' in df.columns:
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    df = df.fillna("")
    return jsonify(df.to_dict(orient="records"))

@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    required = ["date", "category", "amount"]
    missing = [f for f in required if f not in data or not data[f]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    try:
        amount = float(data["amount"])
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Amount must be a number"}), 400
    
    try:
        datetime.strptime(data["date"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400
    
    if data["category"] not in VALID_CATEGORIES:
        return jsonify({
            "error": "Invalid category",
            "valid_categories": VALID_CATEGORIES
        }), 400
    
    new_row = {
        "date": data["date"],
        "category": data["category"],
        "amount": amount,
        "description": data.get("description", "").strip()
    }
    
    df = read_data()
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    
    return jsonify({"status": "created", "expense": new_row}), 201

@app.route("/api/expenses/<int:index>", methods=["DELETE"])
def delete_expense(index):
    df = read_data()
    
    if index < 0 or index >= len(df):
        return jsonify({"error": "Index out of bounds"}), 404

    try:
        df = df.drop(index).reset_index(drop=True)
        save_data(df)
        return jsonify({"status": "deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    df = read_data()
    
    if df.empty:
        return jsonify({
            "total": 0,
            "average": 0,
            "count": 0,
            "top_category": "N/A"
        })

    amount_series = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    
    try:
        category_totals = df.groupby("category")["amount"].sum()
        top_category = category_totals.idxmax()
    except (ValueError, KeyError):
        top_category = "N/A"
    
    return jsonify({
        "total": round(float(amount_series.sum()), 2),
        "average": round(float(amount_series.mean()), 2),
        "count": int(len(df)),
        "top_category": top_category
    })

@app.route("/api/generate", methods=["POST"])
def generate_mock_data():
    """
    Generates 500 records with realistic patterns:
    - Trend: 0.05% daily growth
    - Seasonality: 2x weekend spending on Food & Entertainment
    """
    categories = VALID_CATEGORIES[:-1]
    desc_map = {
        'Food': ['Grocery Store', 'Restaurant', 'Cafe', 'Fast Food'],
        'Transport': ['Uber', 'Metro', 'Bus', 'Taxi'],
        'Entertainment': ['Netflix', 'Cinema', 'Concert', 'Museum'],
        'Health': ['Pharmacy', 'Gym', 'Doctor', 'Supplements'],
        'Bills': ['Electricity', 'Water', 'Internet', 'Phone'],
        'Shopping': ['Amazon', 'Clothing', 'Electronics', 'Books']
    }

    new_data = []
    base_date = datetime.now() - timedelta(days=180)
    
    for i in range(500):
        days_offset = random.randint(0, 180)
        current_date = base_date + timedelta(days=days_offset)
        day_of_week = current_date.weekday()
        
        cat = random.choice(categories)
        
        trend_factor = 1 + (days_offset * 0.0005)
        
        multiplier = 1.0
        if day_of_week >= 5 and cat in ['Food', 'Entertainment']:
            multiplier = 2.0
        
        base_amount = random.uniform(10, 100)
        amount = round(base_amount * trend_factor * multiplier, 2)
        
        desc = random.choice(desc_map[cat])
        
        new_data.append({
            "date": current_date.strftime('%Y-%m-%d'),
            "category": cat,
            "amount": amount,
            "description": desc
        })

    df = pd.DataFrame(new_data)
    save_data(df)
    
    return jsonify({
        "status": "success",
        "message": "Generated 500 records with realistic patterns",
        "features": ["Trend: 0.05% daily growth", "Seasonality: 2x weekend spending"]
    })

@app.route("/api/expenses/clear", methods=["DELETE"])
def clear_all_expenses():
    data = request.get_json() or {}
    confirm = data.get("confirm", False)
    
    if not confirm:
        return jsonify({
            "error": "Confirmation required",
            "hint": "Send {\"confirm\": true} to proceed"
        }), 400
    
    try:
        df = pd.DataFrame(columns=COLUMNS)
        save_data(df)
        return jsonify({
            "status": "success",
            "message": "All expenses cleared"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/forecast")
def get_forecast():
    """
    Holt-Winters Exponential Smoothing forecast.
    Requires min 8 weeks of data.
    """
    if not FORECAST_AVAILABLE:
        return jsonify({
            "error": "Forecasting not available",
            "message": "Install statsmodels: pip install statsmodels"
        }), 503
    
    try:
        data = prepare_data_for_forecast(method='weekly')
        
        if len(data) < 8:
            return jsonify({
                "error": "Insufficient data",
                "message": "Need at least 8 weeks of transaction history",
                "current_weeks": len(data),
                "required_weeks": 8
            }), 400
        
        zero_pct = (data == 0).sum() / len(data)
        if zero_pct > 0.5:
            return jsonify({
                "error": "Data quality issue",
                "message": "Too many weeks without transactions. Add more data.",
                "zero_percentage": round(zero_pct * 100, 1)
            }), 400
        
        # seasonal_periods capped at half dataset length to avoid overfitting
        model = ExponentialSmoothing(
            data,
            trend="add",
            seasonal="add",
            seasonal_periods=min(4, len(data) // 2),
            initialization_method="estimated"
        )
        
        model_fit = model.fit(optimized=True, use_brute=False)
        
        forecast_steps = 4
        forecast_values = model_fit.forecast(forecast_steps)
        
        total_predicted = round(float(forecast_values.sum()), 2)
        
        # Project historical category distribution onto forecast
        history_df = read_data()
        history_df['amount'] = pd.to_numeric(history_df['amount'], errors='coerce').fillna(0)
        
        cat_totals = history_df.groupby('category')['amount'].sum()
        total_history = cat_totals.sum()
        
        if total_history > 0:
            category_shares = cat_totals / total_history
            forecast_pie_data = (category_shares * total_predicted).round(2).to_dict()
        else:
            forecast_pie_data = {}
        
        timeline_data = []
        forecast_dates = pd.date_range(
            start=data.index[-1] + pd.Timedelta(weeks=1),
            periods=forecast_steps,
            freq='W'
        )
        
        for date, value in zip(forecast_dates, forecast_values):
            timeline_data.append({
                "date": date.strftime('%Y-%m-%d'),
                "amount": round(float(value), 2)
            })
        
        return jsonify({
            "total_forecast": total_predicted,
            "forecast_period": "4 weeks",
            "pie": forecast_pie_data,
            "timeline": timeline_data,
            "model": "Holt-Winters Exponential Smoothing",
            "data_points_used": len(data)
        })
        
    except ValueError as e:
        return jsonify({
            "error": "Model fitting failed",
            "message": "Data might not have enough variation or clear seasonal pattern",
            "details": str(e)
        }), 400
    except Exception as e:
        print(f"Forecast Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Forecasting failed",
            "message": str(e)
        }), 500

@app.route("/api/export")
def export_expenses():
    if not EXCEL_EXPORT_AVAILABLE:
        return jsonify({
            "error": "Excel export not available",
            "message": "Install openpyxl: pip install openpyxl"
        }), 503
    
    try:
        df = read_data()
        
        if df.empty:
            return jsonify({"error": "No data to export"}), 400
        
        if 'date' in df.columns:
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Expenses")
            
            summary = pd.DataFrame({
                'Metric': ['Total Spent', 'Average Expense', 'Total Transactions'],
                'Value': [
                    df['amount'].sum(),
                    df['amount'].mean(),
                    len(df)
                ]
            })
            summary.to_excel(writer, index=False, sheet_name="Summary")
            
            category_summary = df.groupby('category')['amount'].agg(['sum', 'mean', 'count'])
            category_summary.columns = ['Total', 'Average', 'Count']
            category_summary.to_excel(writer, sheet_name="By Category")
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'expenses_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        print(f"Export Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify({"categories": VALID_CATEGORIES})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)