"""
Daily Model Training Statistics Slack Reporter
Sends forecasting model performance metrics to Slack after training
"""

import pandas as pd
import numpy as np
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread
import json
import os
import requests
from typing import Dict, List, Tuple
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

SHEET_NAME = "SO & invoice Data merged"

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_merged_data():
    """Load merged SO & Invoice data from Google Sheets"""
    
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    sheet_id = os.environ.get('SPREADSHEET_ID')
    
    if not creds_json or not sheet_id:
        raise ValueError("Missing GOOGLE_CREDENTIALS or SPREADSHEET_ID")
    
    creds_dict = json.loads(creds_json)
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sh = client.open_by_key(sheet_id)
    ws = sh.worksheet(SHEET_NAME)
    rows = ws.get_all_values()
    
    if len(rows) > 1:
        headers = rows[0]
        df = pd.DataFrame(rows[1:], columns=headers)
        df = df.replace('', np.nan)
        return df
    else:
        return pd.DataFrame()

# ══════════════════════════════════════════════════════════════════════════════
# MODEL TRAINING & EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features and target for modeling"""
    
    # Rename columns
    rename_map = {
        'SO - Date Created': 'date',
        'SO - Amount': 'amount',
        'SO - Quantity Ordered': 'qty',
        'SO - Item': 'item',
        'SO - Status': 'status',
        'SO - Calyx || Product Type': 'category',
        'Inv - Amount': 'inv_amount',
        'SO - Customer Companyname': 'customer',
        'Inv - Rep Master': 'inv_rep',
        'SO - Rep Master': 'so_rep'
    }
    
    df = df.rename(columns=rename_map)
    
    # Parse and clean
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
    df['inv_amount'] = pd.to_numeric(df['inv_amount'], errors='coerce').fillna(0)
    
    # Filter
    df = df[df['status'] != 'Cancelled']
    df = df[df['amount'] > 0]
    df = df.dropna(subset=['date'])
    
    # Create time features
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['year'] = df['date'].dt.year
    df['day_of_week'] = df['date'].dt.dayofweek
    
    # Sales rep
    df['sales_rep'] = df['inv_rep'].fillna(df['so_rep'])
    
    # Create categorical features
    df['category_encoded'] = pd.Categorical(df['category']).codes
    df['customer_encoded'] = pd.Categorical(df['customer']).codes
    df['rep_encoded'] = pd.Categorical(df['sales_rep']).codes
    
    # Target: Amount
    y = df['amount']
    
    # Features
    feature_cols = ['month', 'quarter', 'day_of_week', 'category_encoded', 
                    'customer_encoded', 'rep_encoded', 'qty']
    X = df[feature_cols].fillna(0)
    
    return X, y

def train_and_evaluate(X: pd.DataFrame, y: pd.Series) -> Dict:
    """Train model and calculate all statistics"""
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train model
    model = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Calculate metrics
    train_mape = mean_absolute_percentage_error(y_train, y_pred_train) * 100
    test_mape = mean_absolute_percentage_error(y_test, y_pred_test) * 100
    
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    
    # Cross-validation MAPE
    cv_scores = cross_val_score(
        model, X_train, y_train, 
        cv=5, 
        scoring='neg_mean_absolute_percentage_error'
    )
    cv_mape = -cv_scores.mean() * 100
    cv_mape_std = cv_scores.std() * 100
    
    # Confidence interval coverage (90%)
    # Calculate prediction intervals
    residuals = y_test - y_pred_test
    std_residual = np.std(residuals)
    
    # 90% CI is approximately ±1.645 * std
    lower_bound = y_pred_test - 1.645 * std_residual
    upper_bound = y_pred_test + 1.645 * std_residual
    
    # Check coverage
    in_interval = ((y_test >= lower_bound) & (y_test <= upper_bound)).sum()
    ci_coverage = (in_interval / len(y_test)) * 100
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return {
        'samples': {
            'train': len(X_train),
            'test': len(X_test),
            'total': len(X)
        },
        'train': {
            'mape': train_mape,
            'rmse': train_rmse,
            'r2': train_r2
        },
        'test': {
            'mape': test_mape,
            'rmse': test_rmse,
            'r2': test_r2
        },
        'cv': {
            'mape_mean': cv_mape,
            'mape_std': cv_mape_std
        },
        'ci_coverage': ci_coverage,
        'feature_importance': feature_importance.to_dict('records'),
        'model_params': {
            'n_estimators': model.n_estimators,
            'learning_rate': model.learning_rate,
            'max_depth': model.max_depth
        }
    }

# ══════════════════════════════════════════════════════════════════════════════
# SLACK FORMATTING
# ══════════════════════════════════════════════════════════════════════════════

def create_slack_message(stats: Dict) -> Dict:
    """Create formatted Slack message with model stats"""
    
    samples = stats['samples']
    test = stats['test']
    cv = stats['cv']
    ci = stats['ci_coverage']
    features = stats['feature_importance'][:5]  # Top 5 features
    
    # Determine model quality
    if test['mape'] < 10:
        quality = "🟢 Excellent"
    elif test['mape'] < 20:
        quality = "🟡 Good"
    else:
        quality = "🔴 Needs Improvement"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🤖 Daily Model Training Report - {datetime.now().strftime('%Y-%m-%d')}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Model Quality:* {quality}"
            }
        },
        {"type": "divider"}
    ]
    
    # Sample info
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*📊 Training Data*\n```Samples:        {samples['train']} train / {samples['test']} test```"
        }
    })
    
    # Key metrics
    metrics_text = f"""*🎯 Model Performance*
```
  MAPE:           {test['mape']:.1f}%
  RMSE:           ${test['rmse']:.5f}
  R²:             {test['r2']:.3f}
  90% CI Cover:   {ci:.0f}%
  CV MAPE:        {cv['mape_mean']:.1f}% ± {cv['mape_std']:.1f}%
```"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": metrics_text
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Detailed comparison
    comparison_text = f"""*📈 Train vs Test Comparison*
```
                Train       Test
MAPE:          {stats['train']['mape']:6.1f}%     {test['mape']:6.1f}%
RMSE:         ${stats['train']['rmse']:7.5f}   ${test['rmse']:7.5f}
R²:            {stats['train']['r2']:6.3f}      {test['r2']:6.3f}
```"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": comparison_text
        }
    })
    
    # Check for overfitting
    mape_diff = abs(stats['train']['mape'] - test['mape'])
    if mape_diff > 5:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *Warning:* MAPE difference between train/test is {mape_diff:.1f}% - possible overfitting"
            }
        })
    
    blocks.append({"type": "divider"})
    
    # Feature importance
    feature_text = "*🔑 Top 5 Features*\n```\n"
    for feat in features:
        bar = "█" * int(feat['importance'] * 50)
        feature_text += f"{feat['feature']:<20} {bar} {feat['importance']:.3f}\n"
    feature_text += "```"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": feature_text
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Interpretation guide
    interpretation = """*📖 Metric Guide*
• *MAPE* - Mean Absolute Percentage Error (lower is better, <10% is excellent)
• *RMSE* - Root Mean Squared Error (prediction accuracy in $)
• *R²* - Coefficient of determination (higher is better, >0.8 is good)
• *90% CI Cover* - % of actual values within prediction interval (target: 90%)
• *CV MAPE* - Cross-validated error with standard deviation"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": interpretation
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Model config
    params = stats['model_params']
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Model: Gradient Boosting | Estimators: {params['n_estimators']} | LR: {params['learning_rate']} | Depth: {params['max_depth']} | Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p UTC')}"
            }
        ]
    })
    
    return {"blocks": blocks}

def send_to_slack(message: Dict) -> bool:
    """Send message to Slack webhook"""
    
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("⚠️ No SLACK_WEBHOOK_URL found")
        return False
    
    try:
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print("✅ Slack message sent successfully!")
            return True
        else:
            print(f"❌ Slack API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending to Slack: {e}")
        return False

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main execution"""
    print("🚀 Starting model training and evaluation...")
    
    # Load data
    print("📥 Loading data from Google Sheets...")
    raw_df = load_merged_data()
    
    if raw_df.empty:
        print("❌ No data loaded")
        return
    
    print(f"✅ Loaded {len(raw_df):,} rows")
    
    # Prepare features
    print("🔧 Preparing features...")
    X, y = prepare_features(raw_df)
    print(f"✅ Prepared {len(X):,} samples with {X.shape[1]} features")
    
    # Train and evaluate
    print("🤖 Training model and calculating statistics...")
    stats = train_and_evaluate(X, y)
    
    print("\n" + "="*60)
    print("MODEL STATISTICS")
    print("="*60)
    print(f"Samples:        {stats['samples']['train']} train / {stats['samples']['test']} test")
    print(f"  MAPE:           {stats['test']['mape']:.1f}%")
    print(f"  RMSE:           ${stats['test']['rmse']:.5f}")
    print(f"  R²:             {stats['test']['r2']:.3f}")
    print(f"  90% CI Cover:   {stats['ci_coverage']:.0f}%")
    print(f"  CV MAPE:        {stats['cv']['mape_mean']:.1f}% ± {stats['cv']['mape_std']:.1f}%")
    print("="*60)
    
    # Create Slack message
    print("\n💬 Formatting Slack message...")
    message = create_slack_message(stats)
    
    # Send to Slack
    print("📤 Sending to Slack...")
    success = send_to_slack(message)
    
    if success:
        print("🎉 Model training report sent successfully!")
    else:
        print("⚠️ Failed to send report to Slack")

if __name__ == "__main__":
    main()
