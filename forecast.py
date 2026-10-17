"""
Forecasting module for BeTrendy.
Uses scikit-learn Linear Regression on recent search interest history (past 26 weeks)
to forecast the upcoming 8 weeks of consumer search interest.

Generates:
- 8 future weekly predictions (clamped to realistic 0-100 range)
- Trend trajectory label: "Expected to rise", "Expected to hold", or "Expected to fall"
- Extended future date labels
- Model explanation metrics (slope, intercept, R-squared)
- Plain-language evaluator and user disclaimer note
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.linear_model import LinearRegression


DISCLAIMER_NOTE = "Prediction based on past search interest. It is an estimate, not a guarantee."


def forecast_item(
    history_values: List[float],
    forecast_steps: int = 8,
    lookback_window: int = 26
) -> Dict[str, Any]:
    """
    Generate an 8-week predictive trend forecast for a single clothing item.

    Parameters:
        history_values: List of historical weekly interest values (0-100).
        forecast_steps: Number of future weeks to forecast (default 8).
        lookback_window: Number of recent weeks to use for training the model (default 26).

    Returns:
        dict containing:
        - forecast_values: List of predicted values for next 8 weeks.
        - label: 'Expected to rise' | 'Expected to hold' | 'Expected to fall'
        - slope: The rate of change per week
        - r2_score: Coefficient of determination indicating model fit
        - disclaimer: Plain-language note
    """
    if not history_values or len(history_values) < 4:
        raise ValueError("At least 4 historical points are required for forecasting.")

    # Slice the training window (last 26 weeks, or whatever is available)
    window = min(len(history_values), lookback_window)
    recent_y = np.array(history_values[-window:], dtype=float)
    
    # Feature X is the time step [0, 1, ..., window - 1]
    X_train = np.arange(window).reshape(-1, 1)
    y_train = recent_y

    # Train Ordinary Least Squares (OLS) Linear Regression model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Calculate model metrics
    slope = float(model.coef_[0])
    intercept = float(model.intercept_)
    r2 = float(model.score(X_train, y_train))
    r2 = max(0.0, min(1.0, r2))

    # Predict the future 8 weeks [window, window + 1, ..., window + forecast_steps - 1]
    X_future = np.arange(window, window + forecast_steps).reshape(-1, 1)
    y_pred = model.predict(X_future)

    # Clamp predictions to valid Google Trends range [0, 100]
    y_pred_clamped = np.clip(y_pred, 0.0, 100.0)
    forecast_values = [round(float(v), 1) for v in y_pred_clamped]

    # Compare current value with week-8 projection to label expected trajectory
    last_actual = float(history_values[-1])
    end_projection = forecast_values[-1]
    
    pct_change = ((end_projection - last_actual) / max(last_actual, 1.0)) * 100.0

    # Categorize expected future trajectory
    if slope > 0.25 and pct_change >= 5.0:
        label = "Expected to rise"
    elif slope < -0.25 and pct_change <= -5.0:
        label = "Expected to fall"
    else:
        label = "Expected to hold"

    return {
        'forecast_values': forecast_values,
        'label': label,
        'slope': round(slope, 3),
        'intercept': round(intercept, 2),
        'r2_score': round(r2, 2),
        'lookback_weeks': window,
        'forecast_weeks': forecast_steps,
        'disclaimer': DISCLAIMER_NOTE
    }


def generate_future_dates(last_date_str: str, forecast_steps: int = 8) -> List[str]:
    """
    Generate date strings for future weeks starting 7 days after the last historical date.
    Format: YYYY-MM-DD
    """
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    except Exception:
        last_date = datetime.utcnow()

    future_dates = []
    for step in range(1, forecast_steps + 1):
        future_date = last_date + timedelta(weeks=step)
        future_dates.append(future_date.strftime("%Y-%m-%d"))

    return future_dates


def forecast_multiple_items(
    items_dict: Dict[str, List[float]],
    historical_dates: List[str],
    forecast_steps: int = 8
) -> Dict[str, Any]:
    """
    Generate 8-week forecasts for a dictionary of items.
    
    Returns:
        dict containing:
        - historical_dates: list of dates
        - future_dates: list of extended 8 dates
        - all_dates: combined timeline
        - forecasts: mapping of item_name -> forecast dictionary
    """
    last_date_str = historical_dates[-1] if historical_dates else datetime.utcnow().strftime("%Y-%m-%d")
    future_dates = generate_future_dates(last_date_str, forecast_steps)
    all_dates = list(historical_dates) + list(future_dates)

    forecast_results = {}
    for item_name, series in items_dict.items():
        if series and len(series) >= 4:
            forecast_results[item_name] = forecast_item(series, forecast_steps=forecast_steps)

    return {
        'historical_dates': historical_dates,
        'future_dates': future_dates,
        'all_dates': all_dates,
        'forecasts': forecast_results,
        'disclaimer': DISCLAIMER_NOTE
    }
