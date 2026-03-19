# QUICK START GUIDE
## VFR Trip Planner from KBDN

### 🚀 Get Started in 3 Steps

#### 1. Install Dependencies
```bash
pip install requests
```

#### 2. Run Interactive Mode
```bash
python3 vfr_interactive.py
```

#### 3. Choose What You Want to Check
- **Option 1**: See 4-week outlook for local flying
- **Option 2**: Check a specific trip (e.g., KBDN → San Francisco)
- **Option 3**: Find the best flying days in the next 2 weeks

### 📋 Example Usage

#### Check Weekend Trip to San Francisco
```bash
python3 vfr_interactive.py
# Select option 2
# Enter: KSFO
# Enter: 3 (for 3 days ahead)
```

#### See All Favorable Days This Month
```bash
python3 vfr_interactive.py
# Select option 3
```

#### Quick Command Line Check
```bash
python3 vfr_trip_planner.py
```

### 🔔 Set Up Daily Alerts

#### Morning Brief via Email
```bash
crontab -e
# Add this line:
0 6 * * * cd /path/to/scripts && python3 vfr_trip_planner.py | mail -s "Flying Weather" you@email.com
```

#### SMS Alert for Good Days
```bash
# Add to crontab:
0 7 * * * cd /path/to/scripts && python3 vfr_trip_planner.py | mail -s "Flying" 5551234@txt.att.net
```

### ⚙️ Customize for Your RV7

Edit `vfr_trip_planner.py`:

```python
# Your personal minimums
self.criteria = {
    'max_wind': 12,        # Lower if you're conservative with crosswinds
    'min_visibility': 7,   # Increase for mountain flying
    'min_ceiling': 5000,   # Higher for mountain routes
    'max_precip_prob': 20, # Lower if you want clear days only
}
```

### 📍 Add Your Favorite Destinations

```python
self.destinations = {
    'KMMH': {'name': 'Mammoth Lakes', 'coords': (37.6241, -118.8378)},
    'KTVL': {'name': 'South Lake Tahoe', 'coords': (38.8939, -119.9953)},
}
```

### 🌤️ What the System Checks

#### Short-term (1-7 days) - High Confidence
- Winds and gusts at departure and destination
- Visibility conditions
- Precipitation forecasts
- Cloud coverage and ceilings
- Official NOAA aviation weather

#### Long-term (8-16 days) - Medium/Low Confidence  
- Daily weather trends
- Wind patterns
- Precipitation probability
- General conditions for trip planning

### ✈️ Sample Output

```
4-WEEK OUTLOOK: KBDN (Local Flying)
======================================================================

Date         Wind       Gusts      Precip%    Clouds%    Status
----------------------------------------------------------------------
2025-11-17   8.2        12.3       15.0       45.0       ✓ Favorable
2025-11-18   6.5        10.1       10.0       30.0       ✓ Favorable
2025-11-19   18.4       25.6       45.0       75.0       ⚠ Marginal

Found 8 favorable days in the next 16 days

📅 BEST DAYS FOR FLYING:
   2025-11-17: Wind 8kt, Precip 15%, Confidence: medium
   2025-11-18: Wind 7kt, Precip 10%, Confidence: medium
```

### ⚠️ Important Safety Notes

1. **Always get an official weather briefing** before flight
2. **Check NOTAMs** - not included in weather forecasts
3. **Verify TFRs** - especially in California
4. **Long-range forecasts are for planning only** - verify closer to date
5. **You are PIC** - use your judgment for all go/no-go decisions

### 🆘 Troubleshooting

**Can't connect to weather API?**
- Check internet connection
- Try again in a few minutes (API may be temporarily down)

**No favorable days showing?**
- Adjust criteria to be less restrictive
- Winter naturally has fewer VFR days

**Want to see more detail?**
- Check the log files: `tail -f weather_log.txt`
- Run with verbose output: `python3 -v vfr_trip_planner.py`

### 📞 Need Help?

- Read full documentation: `TRIP_PLANNER_README.md`
- Check the original files for all features
- Modify scripts to suit your needs

---

**Happy Flying from KBDN!** ✈️
