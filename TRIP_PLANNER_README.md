# VFR Trip Planner & 4-Week Weather Outlook
### For RV7 Flying from KBDN (Bend Municipal Airport)

An intelligent weather forecasting system that helps you plan VFR flights from your home base (KBDN) by analyzing both short-term aviation weather and long-range forecasts up to 4 weeks ahead.

## 🎯 Key Features

### Short-Term Planning (1-7 days)
- **Detailed Aviation Weather**: Uses NOAA's official aviation weather API
- **Hour-by-hour forecasts**: Wind, visibility, precipitation, cloud conditions
- **Trip Route Analysis**: Checks weather at both departure (KBDN) and destination
- **VFR Criteria Checking**: Automatically evaluates if conditions meet your personal minimums

### Long-Range Planning (8-28 days)
- **4-Week Outlook**: Identifies favorable flying windows weeks in advance
- **Trip Planning Mode**: Plan trips to California and throughout Oregon
- **Trend Analysis**: Daily summaries showing wind, precipitation probability, and cloud cover
- **Confidence Indicators**: Distinguishes between near-term reliable forecasts and longer-range trends

### Home Base Focus
- **KBDN (Bend) as departure point**: All planning assumes you're flying from Bend
- **Pre-configured destinations**: Popular Oregon and California airports
- **Route weather**: Checks conditions at both ends of your flight

## 🚀 Quick Start

### Installation

```bash
# Install required packages
pip install requests

# Make scripts executable
chmod +x vfr_trip_planner.py
chmod +x vfr_interactive.py
```

### Interactive Mode (Recommended)

```bash
python3 vfr_interactive.py
```

This gives you a menu-driven interface to:
1. View 4-week outlook for local flying from KBDN
2. Check specific trip forecasts (e.g., "KBDN → KSFO in 5 days")
3. Find best flying days in the next 2 weeks
4. Check weather for all destinations at once

### Command Line Mode

```bash
# Run the automated trip planner
python3 vfr_trip_planner.py
```

## 📊 What You Get

### 4-Week Outlook Example
```
Date         Wind       Gusts      Precip%    Clouds%    Status
----------------------------------------------------------------------
2025-11-17   8.2        12.3       15.0       45.0       ✓ Favorable
2025-11-18   6.5        10.1       10.0       30.0       ✓ Favorable
2025-11-19   18.4       25.6       45.0       75.0       ⚠ Marginal
2025-11-20   12.1       16.8       20.0       55.0       ✓ Favorable
...

📅 BEST DAYS FOR FLYING:
   2025-11-17: Wind 8kt, Precip 15%, Confidence: medium
   2025-11-18: Wind 7kt, Precip 10%, Confidence: medium
   2025-11-20: Wind 12kt, Precip 20%, Confidence: medium
```

### Trip Forecast Example
```
TRIP FORECAST: KBDN → KSFO
Planning for 3 days ahead
======================================================================

✈️ GOOD TO GO! Trip to San Francisco looks favorable!

Departure (KBDN): Wind 10kt, Visibility >10mi, No significant weather
Destination (KSFO): Wind 12kt, Visibility 10mi, Scattered clouds
```

## 🎮 Usage Scenarios

### Scenario 1: Weekend Trip Planning
You want to fly to San Francisco next weekend:

```python
planner = VFRTripPlanner()
trip = planner.get_trip_forecast('KSFO', days_out=7)
```

### Scenario 2: Find Best Days This Month
You have flexible dates and want to find the best flying days:

```python
outlook = planner.scan_next_weeks()
# Returns list of favorable days with detailed conditions
```

### Scenario 3: Multi-Destination Check
You're flexible on destination and want to see where you can go:

```python
# Use interactive mode option 4
# Checks all destinations and shows which have good weather
```

## ⚙️ Customization

### Adjust Your Personal Minimums

Edit the criteria in `vfr_trip_planner.py`:

```python
self.criteria = {
    'max_wind': 15,        # Your max crosswind comfort (knots)
    'min_visibility': 5,   # Minimum visibility (miles)
    'min_ceiling': 3000,   # Minimum ceiling (feet)
    'max_precip_prob': 30, # Max acceptable precip probability (%)
}
```

### Add New Destinations

Add airports to the destinations dictionary:

```python
self.destinations = {
    'KMMH': {'name': 'Mammoth Lakes', 'coords': (37.6241, -118.8378)},
    'KTRK': {'name': 'Truckee', 'coords': (39.3200, -120.1396)},
    # Add your favorites!
}
```

### Change Home Base

If you're based somewhere other than Bend:

```python
self.home_base = "KPDX"  # Change to your airport
self.home_coords = (45.5887, -122.5975)  # Update coordinates
```

## 📅 Automated Alerts

### Daily Morning Brief (6 AM)
Get your 4-week outlook every morning:

```bash
# Add to crontab (crontab -e)
0 6 * * * cd /path/to/planner && python3 vfr_trip_planner.py >> weather_log.txt 2>&1
```

### Weekend Trip Checker (Friday mornings)
Check weekend flying conditions every Friday:

```bash
0 6 * * 5 cd /path/to/planner && python3 vfr_trip_planner.py | mail -s "Weekend Flying Outlook" your-email@example.com
```

### Find Best Days (Weekly)
Get a list of best flying days each Sunday:

```bash
0 8 * * 0 cd /path/to/planner && python3 -c "from vfr_trip_planner import VFRTripPlanner; p = VFRTripPlanner(); p.scan_next_weeks()" | mail -s "Best Flying Days This Week" your-email@example.com
```

## 🗺️ Pre-Configured Routes from KBDN

### Oregon Destinations
- **KEUG** - Eugene (70 nm W)
- **KPDX** - Portland (130 nm N)
- **KSLE** - Salem (110 nm N)
- **KOTH** - North Bend (170 nm W)
- **KMFR** - Medford (150 nm S)

### California Destinations
- **KSFO** - San Francisco (420 nm S)
- **KOAK** - Oakland (410 nm S)
- **KSMF** - Sacramento (320 nm S)
- **KSNS** - Salinas (470 nm S)
- **KSTS** - Santa Rosa (420 nm S)
- **KSBP** - San Luis Obispo (520 nm S)

## 📈 Understanding Forecast Confidence

### High Confidence (1-3 days)
- Uses official aviation weather (NOAA)
- Very accurate for wind, visibility, precipitation
- Hourly detail available
- **Use for**: Go/No-Go decisions, final flight planning

### Medium Confidence (4-10 days)
- General weather trends
- Good for identifying weather patterns
- Less detailed but still useful
- **Use for**: Planning which days to request off work

### Low Confidence (11-16 days)
- Broad trends only
- Subject to significant change
- Use with caution
- **Use for**: Initial trip planning, watching for patterns

### Beyond 16 Days
- Currently not available (API limitation)
- Check back closer to date
- Consider seasonal averages for Oregon/California

## 🌤️ Seasonal Considerations

### Spring (Mar-May)
- Variable weather, frequent systems
- Good flying between fronts
- Watch for afternoon wind
- Mountain passes may have snow

### Summer (Jun-Aug)
- Generally excellent flying weather
- **Watch for**: Afternoon thunderstorms, high density altitude
- Marine layer on coast (usually clears by 11 AM)
- Best months for VFR in Oregon/California

### Fall (Sep-Nov)
- Transition season, decreasing storms
- Excellent visibility
- **Watch for**: Early season snow in mountains
- Shorter days

### Winter (Dec-Feb)
- Most challenging season
- Frequent IFR conditions
- **Watch for**: Ice, low ceilings, fog
- Fewer flyable days but can be great between systems

## ⚠️ Important RV7-Specific Considerations

### Crosswind Component
- RV7 typically comfortable to 15-20kt direct crosswind
- System checks max winds but not component
- Check runway alignment at destination

### Density Altitude
- Critical in summer, especially southern CA
- System doesn't calculate DA automatically
- KBDN already at 3,460' MSL - add temp consideration

### Fuel Planning
- Range ~900 nm with full tanks
- All configured destinations within range
- **KSFO/KSNS**: Near max range, plan fuel stop

### Mountain Flying
- Most routes from KBDN involve mountains
- Check mountain wave forecasts separately
- Consider higher minimums for mountain routes

## 🔧 Data Sources

### Short-term (1-7 days)
- **NOAA Weather Service API** (api.weather.gov)
- Official US government aviation weather
- Updates every 1-6 hours
- Same data used by Flight Service

### Long-range (8-16 days)
- **Open-Meteo API** (open-meteo.com)
- Free, no API key required
- European forecast model ensemble
- Updates daily

## 📱 Advanced Features

### Email Integration
Modify script to include email notifications:

```python
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'weather@yourdomain.com'
    msg['To'] = 'you@email.com'
    # Add SMTP configuration
```

### SMS Integration
Use email-to-SMS for urgent alerts:
- AT&T: number@txt.att.net
- Verizon: number@vtext.com
- T-Mobile: number@tmomail.net

### Slack/Discord Integration
Post weather updates to team channels:

```python
import requests

def post_to_slack(message):
    webhook_url = "YOUR_WEBHOOK_URL"
    requests.post(webhook_url, json={"text": message})
```

## ❗ Safety Disclaimers

### Always Remember
1. **This is a planning tool only** - NOT a substitute for official weather briefing
2. **Get a full briefing** before every flight from Flight Service or approved sources
3. **Check NOTAMs** - Airspace restrictions not included in weather forecasts
4. **Verify TFRs** - Especially important in California (frequent TFRs)
5. **Long-range forecasts are trends** - Verify closer to flight date
6. **Use your judgment** - You are PIC; make your own go/no-go decision

### What This Tool Doesn't Show
- NOTAMs and airspace restrictions
- TFRs (Temporary Flight Restrictions)
- Winds aloft (important for mountain flying)
- Turbulence forecasts
- Mountain wave activity
- Convective SIGMETs
- Icing forecasts (critical for inadvertent IMC)
- Density altitude calculations
- PIREPs (pilot reports)

## 🐛 Troubleshooting

### "Error fetching forecast"
- Check internet connection
- NOAA API may be temporarily down
- Verify coordinates are correct

### "No favorable days found"
- Adjust criteria to be less restrictive
- Winter months naturally have fewer VFR days
- Check forecasts for different time ranges

### Long-range outlook unavailable
- Open-Meteo API might be down
- Try again in a few minutes
- Check if your IP is rate-limited

## 📚 Additional Resources

### Official Weather Sources
- **Aviation Weather Center**: aviationweather.gov
- **Flight Service**: 1-800-WX-BRIEF
- **NOAA Aviation Weather**: weather.gov/aviation

### Flight Planning Tools
- **ForeFlight**: Comprehensive flight planning (paid)
- **Skyvector**: Free online flight planning
- **Windy**: Excellent wind/weather visualization

### RV7 Resources
- **VAF Forums**: vansairforce.net
- **RV7 Specific**: Performance charts, experiences

## 📞 Support & Contributions

This is an open-source project. Feel free to:
- Modify for your home base
- Add features
- Share improvements
- Report issues

## 📄 Version History

- **v2.0** - Added 4-week outlook, trip planning from KBDN, interactive mode
- **v1.0** - Initial release with current weather checking

---

**Fly safe, plan smart, and enjoy your RV7!** ✈️

*"The superior pilot uses superior judgment to avoid situations requiring superior skill."*
