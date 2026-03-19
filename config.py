# VFR Weather Alert Configuration
# Edit this file to customize your weather alerts

# Airports to monitor (ICAO codes)
# Add or remove airports based on your typical flying routes
AIRPORTS = [
    "KBDN",  # Bend Municipal, OR
    "KEUG",  # Eugene/Mahlon Sweet, OR
    "KPDX",  # Portland International, OR
    "KSLE",  # Salem/McNary Field, OR
    "KOTH",  # North Bend/Southwest Oregon Regional, OR
    "KMFR",  # Medford/Rogue Valley International, OR
    "KSMF",  # Sacramento International, CA
    "KSFO",  # San Francisco International, CA
    "KSNS",  # Salinas Municipal, CA
    "KOAK",  # Oakland International, CA
    "KSAC",  # Sacramento Executive, CA
    "KSTS",  # Santa Rosa/Charles M. Schulz, CA
    "KSBP",  # San Luis Obispo County Regional, CA
]

# Weather thresholds
MAX_WIND_SPEED = 15  # Maximum wind speed in knots
MIN_VISIBILITY = 5   # Minimum visibility in statute miles
MIN_CEILING = 3000   # Minimum ceiling in feet AGL

# Flight categories to accept (VFR, MVFR, IFR, LIFR)
ACCEPTABLE_CATEGORIES = ["VFR", "MVFR"]

# Alert schedule (for reference - set in cron)
# Examples:
# Every day at 6 AM: 0 6 * * *
# Every 3 hours: 0 */3 * * *
# Every morning at 6 and noon: 0 6,12 * * *

# Email settings (optional)
SEND_EMAIL = False
EMAIL_ADDRESS = "your-email@example.com"

# Desktop notifications
SEND_DESKTOP_NOTIFICATION = True

# Logging
LOG_FILE = "weather_alerts.log"
VERBOSE = True
