#!/usr/bin/env python3
"""
VFR Weather Alert System with Desktop Notifications
"""

import subprocess
import platform
from vfr_weather_alert import VFRWeatherChecker

def send_notification(title: str, message: str):
    """Send a desktop notification based on the operating system"""
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            subprocess.run([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}"'
            ])
        elif system == "Linux":
            subprocess.run(['notify-send', title, message])
        elif system == "Windows":
            # Windows notification (requires win10toast package)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            except ImportError:
                print("Install win10toast for Windows notifications: pip install win10toast")
    except Exception as e:
        print(f"Could not send notification: {e}")

def main():
    """Main function with notification support"""
    
    airports = [
        'KBDN',  # Bend, OR
        'KEUG',  # Eugene, OR
        'KPDX',  # Portland, OR
        'KSLE',  # Salem, OR
        'KMFR',  # Medford, OR
        'KSMF',  # Sacramento, CA
        'KSFO',  # San Francisco, CA
    ]
    
    checker = VFRWeatherChecker(airports)
    results = checker.check_all_airports()
    
    # Check for good conditions
    good_airports = [r for r in results if r['is_good']]
    
    if good_airports:
        airport_names = ", ".join([r['airport'] for r in good_airports])
        title = "✈️ Good Flying Weather!"
        message = f"VFR conditions at: {airport_names}"
        
        send_notification(title, message)
        print(f"\n{title}")
        print(message)
        
        # Print detailed info
        alert_message = checker.generate_alert_message(results)
        print(alert_message)
    else:
        print("No ideal flying conditions currently.")

if __name__ == "__main__":
    main()
