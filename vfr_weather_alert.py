#!/usr/bin/env python3
"""
VFR Weather Alert System for RV7 Flying
Checks weather conditions for VFR flying in Oregon and California
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class VFRWeatherChecker:
    def __init__(self, airports: List[str]):
        """
        Initialize weather checker with a list of airport identifiers
        
        Args:
            airports: List of ICAO airport codes (e.g., ['KBDN', 'KEUG', 'KSFO'])
        """
        self.airports = airports
        self.base_url = "https://aviationweather.gov/api/data"
        
    def get_metar(self, airport: str) -> Optional[Dict]:
        """Fetch current METAR for an airport"""
        try:
            url = f"{self.base_url}/metar"
            params = {
                'ids': airport,
                'format': 'json',
                'taf': 'false',
                'hours': '2'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            print(f"Error fetching METAR for {airport}: {e}")
            return None
    
    def get_taf(self, airport: str) -> Optional[Dict]:
        """Fetch TAF (Terminal Area Forecast) for an airport"""
        try:
            url = f"{self.base_url}/taf"
            params = {
                'ids': airport,
                'format': 'json',
                'hours': '24'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            print(f"Error fetching TAF for {airport}: {e}")
            return None
    
    def check_vfr_conditions(self, metar_data: Dict) -> Dict:
        """
        Check if conditions meet VFR criteria for flying
        
        Criteria:
        - Winds < 15 knots
        - Ceiling > 3000 ft AGL or clear/high overcast
        - Visibility > 5 miles
        - Flight category VFR or MVFR
        """
        result = {
            'airport': metar_data.get('icaoId', 'Unknown'),
            'is_good': False,
            'conditions': {},
            'issues': [],
            'raw_metar': metar_data.get('rawOb', ''),
            'time': metar_data.get('reportTime', '')
        }
        
        # Check wind speed
        wind_speed = metar_data.get('wspd', 0)
        wind_gust = metar_data.get('wgst', 0)
        max_wind = max(wind_speed, wind_gust) if wind_gust else wind_speed
        
        result['conditions']['wind_speed'] = wind_speed
        result['conditions']['wind_gust'] = wind_gust
        
        if max_wind > 15:
            result['issues'].append(f"Winds too strong: {max_wind} knots")
        
        # Check ceiling
        ceiling = metar_data.get('ceil')
        cloud_layers = metar_data.get('clouds', [])
        
        result['conditions']['ceiling'] = ceiling if ceiling else 'Unlimited'
        result['conditions']['clouds'] = cloud_layers
        
        # Check for low ceilings or overcast below 3000 ft
        low_overcast = False
        if ceiling and ceiling < 3000:
            result['issues'].append(f"Ceiling too low: {ceiling} ft")
            low_overcast = True
        
        # Check visibility
        visibility = metar_data.get('visib', 10)
        result['conditions']['visibility'] = visibility
        
        if visibility < 5:
            result['issues'].append(f"Visibility too low: {visibility} miles")
        
        # Check flight category
        flight_category = metar_data.get('fltcat', 'UNKNOWN')
        result['conditions']['flight_category'] = flight_category
        
        if flight_category not in ['VFR', 'MVFR']:
            result['issues'].append(f"Flight category: {flight_category}")
        
        # Determine if conditions are good
        result['is_good'] = (
            max_wind <= 15 and
            visibility >= 5 and
            not low_overcast and
            flight_category in ['VFR', 'MVFR']
        )
        
        return result
    
    def check_all_airports(self) -> List[Dict]:
        """Check weather conditions for all configured airports"""
        results = []
        
        for airport in self.airports:
            print(f"\nChecking weather for {airport}...")
            metar = self.get_metar(airport)
            
            if metar:
                check_result = self.check_vfr_conditions(metar)
                results.append(check_result)
            else:
                print(f"Could not retrieve weather for {airport}")
        
        return results
    
    def generate_alert_message(self, results: List[Dict]) -> str:
        """Generate a formatted alert message"""
        good_airports = [r for r in results if r['is_good']]
        
        message = f"\n{'='*70}\n"
        message += f"VFR WEATHER ALERT - {datetime.now().strftime('%Y-%m-%d %H:%M')} PST\n"
        message += f"{'='*70}\n\n"
        
        if good_airports:
            message += "🟢 GOOD FLYING CONDITIONS AT:\n\n"
            for result in good_airports:
                message += f"  {result['airport']}:\n"
                message += f"    Wind: {result['conditions']['wind_speed']} kt"
                if result['conditions']['wind_gust']:
                    message += f" (gusts {result['conditions']['wind_gust']} kt)"
                message += "\n"
                message += f"    Visibility: {result['conditions']['visibility']} miles\n"
                message += f"    Ceiling: {result['conditions']['ceiling']}\n"
                message += f"    Flight Category: {result['conditions']['flight_category']}\n"
                message += f"    METAR: {result['raw_metar']}\n\n"
        
        # Report on airports with issues
        bad_airports = [r for r in results if not r['is_good']]
        if bad_airports:
            message += "🔴 CONDITIONS NOT MET AT:\n\n"
            for result in bad_airports:
                message += f"  {result['airport']}:\n"
                for issue in result['issues']:
                    message += f"    - {issue}\n"
                message += f"    METAR: {result['raw_metar']}\n\n"
        
        message += f"{'='*70}\n"
        
        return message


def main():
    """Main function to run weather checks"""
    
    # Configure airports in Oregon and California
    # Adjust this list based on your typical routes
    airports = [
        'KBDN',  # Bend, OR
        'KEUG',  # Eugene, OR
        'KPDX',  # Portland, OR
        'KSLE',  # Salem, OR
        'KOTH',  # North Bend/Coos Bay, OR
        'KMFR',  # Medford, OR
        'KSMF',  # Sacramento, CA
        'KSFO',  # San Francisco, CA
        'KSNS',  # Salinas, CA
        'KOAK',  # Oakland, CA
        'KSBP',  # San Luis Obispo, CA
    ]
    
    print("VFR Weather Alert System for RV7 Flying")
    print("Checking weather conditions...\n")
    
    checker = VFRWeatherChecker(airports)
    results = checker.check_all_airports()
    
    message = checker.generate_alert_message(results)
    print(message)
    
    # Check if any airports have good conditions
    good_conditions = any(r['is_good'] for r in results)
    
    if good_conditions:
        print("\n✈️  Great day for flying! Check NOTAMS before departure.")
    else:
        print("\n⛔ No airports currently meeting ideal VFR conditions.")
    
    return good_conditions


if __name__ == "__main__":
    main()
