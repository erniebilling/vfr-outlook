# VFR Weather Alert System for RV7 Flying

An automated weather monitoring system that alerts you when conditions are ideal for VFR flying in Oregon and California.

## Features

- ✈️ Monitors multiple airports along your typical routes
- 🌤️ Checks for favorable VFR conditions (light winds, good visibility, high ceilings)
- 📊 Uses official aviation weather data (METAR/TAF from aviationweather.gov)
- 🔔 Desktop notifications when conditions are good
- 📧 Optional email alerts
- ⚙️ Customizable thresholds for wind, visibility, and ceiling

## Weather Criteria

The system alerts you when ALL of the following conditions are met:

- **Winds:** ≤ 15 knots (including gusts)
- **Visibility:** ≥ 5 statute miles
- **Ceiling:** > 3,000 ft AGL or clear/high overcast
- **Flight Category:** VFR or MVFR

## Quick Start

### 1. Install Python Dependencies

```bash
pip install requests --break-system-packages
```

For desktop notifications on macOS, no additional packages needed (uses osascript).
For Linux, ensure `notify-send` is installed (usually comes with desktop environments).
For Windows, install: `pip install win10toast`

### 2. Test the System

Run manually to check current conditions:

```bash
python3 vfr_weather_alert.py
```

You should see a report of weather conditions at all configured airports.

### 3. Customize Your Airports

Edit `config.py` to add/remove airports or adjust thresholds:

```python
AIRPORTS = [
    "KBDN",  # Bend, OR
    "KEUG",  # Eugene, OR
    # Add your frequently visited airports
]

MAX_WIND_SPEED = 15  # Adjust based on your comfort level
```

## Setup Options

### Option 1: Manual Checks

Run whenever you're planning a flight:

```bash
python3 vfr_weather_alert.py
```

### Option 2: Scheduled Checks with Cron

Set up automated alerts using cron. Edit your crontab:

```bash
crontab -e
```

Add one of these lines:

```bash
# Check every morning at 6 AM
0 6 * * * cd /path/to/weather-alerts && python3 vfr_weather_alert.py >> weather_alerts.log 2>&1

# Check every 3 hours (6 AM, 9 AM, 12 PM, 3 PM, 6 PM)
0 6,9,12,15,18 * * * cd /path/to/weather-alerts && python3 vfr_weather_alert.py >> weather_alerts.log 2>&1

# Desktop notification every 3 hours
0 */3 * * * cd /path/to/weather-alerts && DISPLAY=:0 python3 vfr_weather_alert_desktop.py
```

### Option 3: Email Alerts

If you have mail configured on your system:

```bash
# Email yourself at 6 AM and noon
0 6,12 * * * cd /path/to/weather-alerts && python3 vfr_weather_alert.py | mail -s "VFR Weather Alert" your-email@example.com
```

### Option 4: SMS Alerts via Email-to-SMS

Most carriers offer email-to-SMS gateways:

- AT&T: number@txt.att.net
- T-Mobile: number@tmomail.net
- Verizon: number@vtext.com
- Sprint: number@messaging.sprintpcs.com

```bash
0 6 * * * cd /path/to/weather-alerts && python3 vfr_weather_alert.py | mail -s "Flying Weather" 5551234567@txt.att.net
```

## Configured Airports

The default configuration includes these airports along the Oregon-California corridor:

**Oregon:**
- KBDN - Bend Municipal
- KEUG - Eugene/Mahlon Sweet
- KPDX - Portland International
- KSLE - Salem/McNary Field
- KOTH - North Bend/Southwest Oregon Regional
- KMFR - Medford/Rogue Valley International

**California:**
- KSMF - Sacramento International
- KSFO - San Francisco International
- KSNS - Salinas Municipal
- KOAK - Oakland International
- KSAC - Sacramento Executive
- KSTS - Santa Rosa/Charles M. Schulz

## Advanced Customization

### Adjust Weather Thresholds

For your RV7, you might want to adjust thresholds based on your experience and comfort level:

```python
# In vfr_weather_alert.py, modify check_vfr_conditions():

MAX_WIND_SPEED = 12  # More conservative for crosswinds
MIN_VISIBILITY = 7   # Better for scenic flights
MIN_CEILING = 5000   # For mountain flying
```

### Add Density Altitude Checks

Modify the script to calculate density altitude and warn about high DA conditions (important for performance).

### Filter by Wind Direction

Add logic to check crosswind components for specific runways at your departure airport.

## Understanding the Output

The alert includes:

```
🟢 GOOD FLYING CONDITIONS AT:

  KBDN:
    Wind: 8 kt
    Visibility: 10 miles
    Ceiling: Unlimited
    Flight Category: VFR
    METAR: KBDN 161453Z 27008KT 10SM CLR 15/01 A3015

🔴 CONDITIONS NOT MET AT:

  KSFO:
    - Winds too strong: 22 knots
    - Ceiling too low: 1200 ft
```

## Important Notes for RV7 Pilots

1. **Always check NOTAMs** before flight, even if weather is good
2. **Verify winds aloft** - surface winds may be calm but upper winds can affect your flight
3. **Check density altitude** on hot days, especially at higher elevation airports
4. **Mountain flying** - Consider higher minimums for mountain routes
5. **Marine layer** - Coastal California airports often have morning fog/low clouds
6. **Afternoon thunderstorms** - Common in summer months
7. **TFRs** - Check for temporary flight restrictions, especially in California

## Troubleshooting

**Script returns no data:**
- Check internet connection
- Verify airport codes are correct (must be ICAO format, e.g., KBDN not just BND)
- aviationweather.gov API may be temporarily unavailable

**Desktop notifications not working:**
- macOS: Ensure Terminal/iTerm has notification permissions
- Linux: Install libnotify-bin (`sudo apt install libnotify-bin`)
- Windows: Install win10toast (`pip install win10toast`)

**Cron job not running:**
- Use full paths in crontab
- Check system logs: `grep CRON /var/log/syslog`
- Ensure script is executable: `chmod +x vfr_weather_alert.py`

## Data Source

Weather data is sourced from the official Aviation Weather Center (aviationweather.gov), which provides the same METAR and TAF data used for flight planning.

## Safety Disclaimer

This tool is intended as a convenience for initial weather screening only. Always:
- Check official weather briefings before flight
- Get a full briefing from Flight Service or approved sources
- Check NOTAMs, TFRs, and other airspace restrictions
- Make your own pilot-in-command decisions
- Never rely solely on automated alerts for flight planning

Blue skies and tailwinds! ✈️

## License

Free to use and modify for personal aviation use.
