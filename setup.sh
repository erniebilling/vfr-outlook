#!/bin/bash
# VFR Weather Alert Setup Script

echo "VFR Weather Alert System Setup"
echo "================================"
echo ""
echo "This script will help you set up automated weather alerts."
echo ""

# Make the Python script executable
chmod +x vfr_weather_alert.py

echo "✓ Made weather script executable"
echo ""

# Test the script
echo "Testing the weather alert script..."
python3 vfr_weather_alert.py

echo ""
echo "================================"
echo "SETUP OPTIONS"
echo "================================"
echo ""
echo "Option 1: Run manually whenever you want"
echo "  Simply run: python3 vfr_weather_alert.py"
echo ""
echo "Option 2: Set up automated checks with cron"
echo "  Example: Check every morning at 6 AM"
echo "  Add this line to your crontab (run 'crontab -e'):"
echo "  0 6 * * * cd $(pwd) && python3 vfr_weather_alert.py >> weather_alerts.log 2>&1"
echo ""
echo "Option 3: Email notifications (requires mail setup)"
echo "  Add this to crontab for email alerts:"
echo "  0 6,12,18 * * * cd $(pwd) && python3 vfr_weather_alert.py | mail -s 'VFR Weather Alert' your-email@example.com"
echo ""
echo "Option 4: Desktop notifications (for Linux/Mac)"
echo "  Add this to crontab:"
echo "  0 */3 * * * cd $(pwd) && DISPLAY=:0 python3 vfr_weather_alert_desktop.py"
echo ""
echo "================================"
echo "CUSTOMIZATION"
echo "================================"
echo ""
echo "To customize airports, edit vfr_weather_alert.py and modify the 'airports' list"
echo "To adjust wind/visibility thresholds, modify the check_vfr_conditions() function"
echo ""
echo "For your RV7, you might also want to consider:"
echo "  - Density altitude warnings (hot days at high elevation)"
echo "  - Crosswind component calculations"
echo "  - Turbulence forecasts"
echo ""
