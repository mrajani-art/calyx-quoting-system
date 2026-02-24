"""
Daily Model Training Statistics from Saved Metrics
Reads metrics from models/*.joblib files and sends to Slack
"""

import joblib
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# LOAD MODEL METRICS
# ══════════════════════════════════════════════════════════════════════════════

def load_vendor_metrics(vendor_name: str) -> dict:
    """Load metrics for a specific vendor"""
    
    models_dir = Path("models")
    
    try:
        # Load metrics file
        metrics_file = models_dir / f"{vendor_name}_metrics.joblib"
        if not metrics_file.exists():
            return None
        
        metrics = joblib.load(metrics_file)
        
        # Load feature importance
        importance_file = models_dir / f"{vendor_name}_importances.joblib"
        if importance_file.exists():
            importances = joblib.load(importance_file)
        else:
            importances = {}
        
        # Load features list
        features_file = models_dir / f"{vendor_name}_features.joblib"
        if features_file.exists():
            features = joblib.load(features_file)
        else:
            features = []
        
        return {
            'vendor': vendor_name,
            'metrics': metrics,
            'importances': importances,
            'features': features
        }
        
    except Exception as e:
        print(f"❌ Error loading {vendor_name} metrics: {e}")
        return None

def load_all_metrics() -> list:
    """Load metrics for all vendors"""
    
    models_dir = Path("models")
    if not models_dir.exists():
        print("❌ Models directory not found")
        return []
    
    # Find all vendor metrics files
    vendors = []
    for metrics_file in models_dir.glob("*_metrics.joblib"):
        vendor_name = metrics_file.stem.replace("_metrics", "")
        vendors.append(vendor_name)
    
    # Load metrics for each vendor
    all_metrics = []
    for vendor in vendors:
        vendor_data = load_vendor_metrics(vendor)
        if vendor_data:
            all_metrics.append(vendor_data)
    
    return all_metrics

# ══════════════════════════════════════════════════════════════════════════════
# SLACK FORMATTING
# ══════════════════════════════════════════════════════════════════════════════

def format_metric(value: float, is_percentage: bool = False) -> str:
    """Format metric value"""
    if is_percentage:
        return f"{value:.1f}%"
    else:
        return f"{value:.3f}"

def get_quality_indicator(mape: float) -> str:
    """Get quality indicator based on MAPE"""
    if mape < 10:
        return "🟢 Excellent"
    elif mape < 20:
        return "🟡 Good"
    else:
        return "🔴 Needs Improvement"

def create_vendor_section(vendor_data: dict) -> list:
    """Create Slack blocks for a vendor"""
    
    vendor = vendor_data['vendor']
    metrics = vendor_data['metrics']
    importances = vendor_data['importances']
    features = vendor_data['features']
    
    blocks = []
    
    # Check if log transformation was used
    use_log = metrics.get('use_log_target', False)
    
    # Vendor header
    log_note = " (Log-transformed)" if use_log else ""
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*📦 {vendor.upper()} Model{log_note}*"
        }
    })
    
    # Metrics - use actual keys from your joblib files
    mape = metrics.get('mape', 0)  # Already in percentage format (7.45 not 0.0745)
    rmse = metrics.get('rmse', 0)
    r2 = metrics.get('r2', 0)
    coverage_90 = metrics.get('coverage_90', 0)  # 90% CI coverage
    
    # Cross-validation - already in percentage
    cv_mape = metrics.get('cv_mape_mean', 0)
    cv_std = metrics.get('cv_mape_std', 0)
    
    # Sample counts
    n_train = metrics.get('n_train', 0)
    n_test = metrics.get('n_test', 0)
    
    quality = get_quality_indicator(mape)
    
    metrics_text = f"""*Quality:* {quality}

```
Samples:        {n_train} train / {n_test} test
  MAPE:           {mape:.1f}%
  RMSE:           ${rmse:.5f}
  R²:             {r2:.3f}
  90% CI Cover:   {coverage_90:.0f}%
  CV MAPE:        {cv_mape:.1f}% ± {cv_std:.1f}%
```"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": metrics_text
        }
    })
    
    # Feature importance (top 5)
    if importances and features:
        # Sort features by importance
        feature_imp = [(feat, importances.get(feat, 0)) for feat in features]
        feature_imp.sort(key=lambda x: x[1], reverse=True)
        top_5 = feature_imp[:5]
        
        feature_text = "*🔑 Top 5 Features*\n```\n"
        for feat, imp in top_5:
            bar = "█" * int(imp * 50)
            feature_text += f"{feat:<20} {bar} {imp:.3f}\n"
        feature_text += "```"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": feature_text
            }
        })
    
    blocks.append({"type": "divider"})
    
    return blocks

def create_slack_message(all_metrics: list) -> dict:
    """Create formatted Slack message"""
    
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
                "text": f"*Vendor Pricing Models - Latest Training Results*"
            }
        },
        {"type": "divider"}
    ]
    
    # Add section for each vendor
    for vendor_data in all_metrics:
        vendor_blocks = create_vendor_section(vendor_data)
        blocks.extend(vendor_blocks)
    
    # Summary
    total_vendors = len(all_metrics)
    avg_mape = sum(v['metrics'].get('mape', 0) for v in all_metrics) / total_vendors if total_vendors > 0 else 0
    
    summary_text = f"""*📊 Overall Summary*
```
Vendors Trained:    {total_vendors}
Average MAPE:       {avg_mape:.1f}%
```"""
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": summary_text
        }
    })
    
    # Metric guide
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": """*📖 Metric Guide*
• *MAPE* - Mean Absolute Percentage Error (lower is better, <10% is excellent)
• *RMSE* - Root Mean Squared Error (prediction accuracy in $)
• *R²* - Coefficient of determination (higher is better, >0.8 is good)
• *90% CI Cover* - % of actual values within prediction interval (target: 90%)
• *CV MAPE* - Cross-validated error in log-space (not directly comparable to MAPE)"""
        }
    })
    
    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p UTC')} | Source: models/*.joblib files"
            }
        ]
    })
    
    return {"blocks": blocks}

# ══════════════════════════════════════════════════════════════════════════════
# SLACK SENDING
# ══════════════════════════════════════════════════════════════════════════════

def send_to_slack(message: dict) -> bool:
    """Send message to Slack webhook"""
    
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("⚠️ No SLACK_WEBHOOK_URL found in environment variables")
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
    print("🚀 Starting model metrics reporting...")
    
    # Load all vendor metrics
    print("📥 Loading model metrics from models/ directory...")
    all_metrics = load_all_metrics()
    
    if not all_metrics:
        print("❌ No model metrics found")
        return
    
    print(f"✅ Loaded metrics for {len(all_metrics)} vendors")
    
    # Print summary to console
    print("\n" + "="*60)
    print("MODEL METRICS SUMMARY")
    print("="*60)
    for vendor_data in all_metrics:
        vendor = vendor_data['vendor']
        metrics = vendor_data['metrics']
        
        mape = metrics.get('mape', 0)
        rmse = metrics.get('rmse', 0)
        r2 = metrics.get('r2', 0)
        coverage_90 = metrics.get('coverage_90', 0)
        n_train = metrics.get('n_train', 0)
        n_test = metrics.get('n_test', 0)
        
        print(f"\n{vendor.upper()}:")
        print(f"  Samples:  {n_train} train / {n_test} test")
        print(f"  MAPE:     {mape:.1f}%")
        print(f"  RMSE:     ${rmse:.5f}")
        print(f"  R²:       {r2:.3f}")
        print(f"  90% CI:   {coverage_90:.0f}%")
    print("="*60)
    
    # Create Slack message
    print("\n💬 Formatting Slack message...")
    message = create_slack_message(all_metrics)
    
    # Send to Slack
    print("📤 Sending to Slack...")
    success = send_to_slack(message)
    
    if success:
        print("🎉 Model metrics report sent successfully!")
    else:
        print("⚠️ Failed to send report to Slack")

if __name__ == "__main__":
    main()
