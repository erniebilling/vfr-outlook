#!/bin/bash
# Automated Weather Alert Setup for VFR Trip Planning

echo "VFR Trip Planner - Automated Alert Setup"
echo "========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Current directory: $SCRIPT_DIR"
echo ""
echo "Choose your alert schedule:"
echo ""
echo "1. Daily morning brief (6 AM) - Full 4-week outlook"
echo "2. Find best flying days (Sunday 8 AM)"
echo "3. Check specific destination (daily)"
echo "4. Weekend outlook (Friday 6 PM)"
echo "5. Custom schedule"
echo "6. Show example crontab entries"
echo ""

read -p "Select option (1-6): " option

case $option in
    1)
        echo ""
        echo "Daily Morning Brief (6 AM)"
        echo "Add this line to your crontab (run 'crontab -e'):"
        echo ""
        echo "0 6 * * * cd $SCRIPT_DIR && python3 vfr_trip_planner.py >> weather_log.txt 2>&1"
        echo ""
        ;;
    2)
        echo ""
        echo "Weekly Best Days (Sunday 8 AM)"
        echo "Add this line to your crontab:"
        echo ""
        echo "0 8 * * 0 cd $SCRIPT_DIR && python3 vfr_trip_planner.py | mail -s 'Best Flying Days This Week' your-email@example.com"
        echo ""
        ;;
    3)
        echo ""
        read -p "Enter destination airport (e.g., KSFO): " dest
        read -p "Days ahead to check (e.g., 3): " days
        read -p "Hour to check (0-23): " hour
        echo ""
        echo "Add this line to your crontab:"
        echo ""
        echo "0 $hour * * * cd $SCRIPT_DIR && python3 -c \"from vfr_trip_planner import VFRTripPlanner; p = VFRTripPlanner(); t = p.get_trip_forecast('$dest', $days)\" >> weather_log.txt 2>&1"
        echo ""
        ;;
    4)
        echo ""
        echo "Weekend Outlook (Friday 6 PM)"
        echo "Add this line to your crontab:"
        echo ""
        echo "0 18 * * 5 cd $SCRIPT_DIR && python3 vfr_trip_planner.py | mail -s 'Weekend Flying Outlook from KBDN' your-email@example.com"
        echo ""
        ;;
    5)
        echo ""
        echo "Custom Schedule"
        echo "Cron format: MIN HOUR DAY MONTH WEEKDAY"
        echo "Examples:"
        echo "  0 6 * * *     = Every day at 6 AM"
        echo "  0 */3 * * *   = Every 3 hours"
        echo "  0 6,18 * * *  = 6 AM and 6 PM daily"
        echo "  0 8 * * 0,3,5 = 8 AM Sunday, Wednesday, Friday"
        echo ""
        read -p "Enter your cron schedule: " schedule
        echo ""
        echo "Add this line to your crontab:"
        echo ""
        echo "$schedule cd $SCRIPT_DIR && python3 vfr_trip_planner.py >> weather_log.txt 2>&1"
        echo ""
        ;;
    6)
        cat << 'EOF'

EXAMPLE CRONTAB ENTRIES
=======================

# Daily morning weather brief at 6 AM
0 6 * * * cd /path/to/planner && python3 vfr_trip_planner.py >> weather_log.txt 2>&1

# Email brief every morning
0 6 * * * cd /path/to/planner && python3 vfr_trip_planner.py | mail -s "VFR Outlook from KBDN" you@email.com

# SMS alert (via email-to-SMS) for good flying days
0 7 * * * cd /path/to/planner && python3 -c "from vfr_trip_planner import VFRTripPlanner; p = VFRTripPlanner(); o = p.scan_next_weeks(); good = [d['date'] for d in o.get('favorable_days', [])[:3]]; print('Good flying: ' + ', '.join(good) if good else 'No good days soon')" | mail -s "Flying" 5551234567@txt.att.net

# Check San Francisco trip in 3 days (every morning)
0 6 * * * cd /path/to/planner && python3 -c "from vfr_trip_planner import VFRTripPlanner; p = VFRTripPlanner(); t = p.get_trip_forecast('KSFO', 3); print('Trip favorable!' if t['route_favorable'] else 'Check weather')" | mail -s "SFO Trip" you@email.com

# Weekend outlook on Friday evening
0 18 * * 5 cd /path/to/planner && python3 vfr_trip_planner.py | mail -s "Weekend Flying" you@email.com

# Interactive mode with desktop notification (requires display)
0 */3 * * * DISPLAY=:0 cd /path/to/planner && python3 vfr_interactive.py < /dev/null

# Log to file for later review
0 6,12,18 * * * cd /path/to/planner && python3 vfr_trip_planner.py >> weather_history.log 2>&1

EOF
        echo ""
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "To edit your crontab, run: crontab -e"
echo "To view current crontab, run: crontab -l"
echo ""
echo "TIPS:"
echo "- Use full paths in crontab entries"
echo "- Set up email (mailx) for email alerts"
echo "- Check logs regularly: tail -f weather_log.txt"
echo "- Test commands manually before adding to cron"
echo ""
echo "For SMS alerts, use your carrier's email-to-SMS gateway:"
echo "  AT&T:     number@txt.att.net"
echo "  Verizon:  number@vtext.com"
echo "  T-Mobile: number@tmomail.net"
echo "  Sprint:   number@messaging.sprintpcs.com"
echo ""
