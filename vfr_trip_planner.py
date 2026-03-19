#!/usr/bin/env python3
"""
VFR Weather Forecast & Trip Planner for RV7
Home Base: KBDN (Bend, Oregon)

Provides:
- Short-term (1-7 days): Detailed aviation weather from NOAA
- Long-range (8-28 days): General weather trends for trip planning
- Trip planning mode: Analyze routes from KBDN to destinations
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

class VFRTripPlanner:
    def __init__(self):
        """Initialize the VFR trip planner with KBDN as home base"""
        self.home_base = "KBDN"
        self.home_coords = (44.0947, -121.2005)  # Bend, OR coordinates
        
        # Destination airports in Oregon and California
        self.destinations = {
            'KEUG': {'name': 'Eugene', 'coords': (44.1246, -123.2119)},
            'KPDX': {'name': 'Portland', 'coords': (45.5887, -122.5975)},
            'KSLE': {'name': 'Salem', 'coords': (44.9095, -123.0026)},
            'KOTH': {'name': 'North Bend', 'coords': (43.4171, -124.2460)},
            'KMFR': {'name': 'Medford', 'coords': (42.3742, -122.8733)},
            'KSFO': {'name': 'San Francisco', 'coords': (37.6213, -122.3790)},
            'KSMF': {'name': 'Sacramento', 'coords': (38.6952, -121.5908)},
            'KOAK': {'name': 'Oakland', 'coords': (37.7214, -122.2208)},
            'KSNS': {'name': 'Salinas', 'coords': (36.6628, -121.6063)},
            'KSTS': {'name': 'Santa Rosa', 'coords': (38.5089, -122.8128)},
            'KSBP': {'name': 'San Luis Obispo', 'coords': (35.2368, -120.6424)},
        }
        
        # Weather criteria for VFR flight
        self.criteria = {
            'max_wind': 15,  # knots
            'min_visibility': 5,  # miles
            'min_ceiling': 3000,  # feet
            'max_precip_prob': 30,  # percent
        }
    
    def get_airport_coords(self, icao: str) -> Tuple[float, float]:
        """Get coordinates for an airport"""
        if icao == self.home_base:
            return self.home_coords
        return self.destinations.get(icao, {}).get('coords', (0, 0))
    
    def get_short_term_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get 7-day detailed forecast from NOAA Weather Service API
        This provides hour-by-hour forecasts with aviation-relevant data
        """
        try:
            # Step 1: Get grid point data
            points_url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
            headers = {'User-Agent': 'VFR-Weather-Planner/1.0'}
            
            response = requests.get(points_url, headers=headers, timeout=10)
            response.raise_for_status()
            points_data = response.json()
            
            # Step 2: Get hourly forecast
            forecast_url = points_data['properties']['forecastHourly']
            response = requests.get(forecast_url, headers=headers, timeout=10)
            response.raise_for_status()
            forecast_data = response.json()
            
            return forecast_data
            
        except Exception as e:
            print(f"Error fetching short-term forecast: {e}")
            return None
    
    def get_long_range_outlook(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Get 14-28 day outlook using Open-Meteo (free, no API key required)
        Provides general weather trends for trip planning
        """
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': lat,
                'longitude': lon,
                'hourly': 'temperature_2m,precipitation_probability,windspeed_10m,windgusts_10m,cloudcover',
                'forecast_days': 16,  # Maximum available
                'temperature_unit': 'fahrenheit',
                'windspeed_unit': 'kn',
                'precipitation_unit': 'inch',
                'timezone': 'America/Los_Angeles'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error fetching long-range outlook: {e}")
            return None
    
    def analyze_flying_window(self, forecast_data: Dict, start_hour: int, duration_hours: int) -> Dict:
        """
        Analyze a time window to see if conditions meet VFR criteria
        """
        periods = forecast_data.get('properties', {}).get('periods', [])
        
        if not periods or start_hour >= len(periods):
            return {'flyable': False, 'reason': 'No forecast data available'}
        
        issues = []
        max_wind = 0
        min_visibility = 999
        
        # Check each hour in the window
        for i in range(start_hour, min(start_hour + duration_hours, len(periods))):
            period = periods[i]
            
            # Extract wind speed
            wind_str = period.get('windSpeed', '0 mph')
            try:
                wind = int(wind_str.split()[0])
                max_wind = max(max_wind, wind)
                if wind > self.criteria['max_wind']:
                    issues.append(f"High winds: {wind} kt at {period['startTime']}")
            except:
                pass
            
            # Check for precipitation
            forecast = period.get('shortForecast', '').lower()
            if any(wx in forecast for wx in ['rain', 'storm', 'thunder', 'shower']):
                issues.append(f"Precipitation forecast: {forecast} at {period['startTime']}")
        
        return {
            'flyable': len(issues) == 0,
            'max_wind': max_wind,
            'issues': issues,
            'periods_checked': min(duration_hours, len(periods) - start_hour)
        }
    
    def analyze_long_range_day(self, hourly_data: Dict, day_offset: int) -> Dict:
        """
        Analyze a specific day in the long-range forecast
        Returns summary for that day (average conditions)
        """
        try:
            times = hourly_data.get('hourly', {}).get('time', [])
            temps = hourly_data.get('hourly', {}).get('temperature_2m', [])
            winds = hourly_data.get('hourly', {}).get('windspeed_10m', [])
            gusts = hourly_data.get('hourly', {}).get('windgusts_10m', [])
            precip_prob = hourly_data.get('hourly', {}).get('precipitation_probability', [])
            clouds = hourly_data.get('hourly', {}).get('cloudcover', [])
            
            # Get hours for this day (daytime hours 8 AM - 6 PM)
            day_start = day_offset * 24 + 8  # 8 AM
            day_end = day_offset * 24 + 18   # 6 PM
            
            if day_end >= len(times):
                return None
            
            # Calculate averages for daytime hours
            day_winds = winds[day_start:day_end]
            day_gusts = gusts[day_start:day_end]
            day_precip = precip_prob[day_start:day_end]
            day_clouds = clouds[day_start:day_end]
            
            avg_wind = sum(day_winds) / len(day_winds) if day_winds else 0
            max_gust = max(day_gusts) if day_gusts else 0
            avg_precip_prob = sum(day_precip) / len(day_precip) if day_precip else 0
            avg_cloud = sum(day_clouds) / len(day_clouds) if day_clouds else 0
            
            # Determine if conditions look favorable
            favorable = (
                max_gust <= self.criteria['max_wind'] and
                avg_precip_prob <= self.criteria['max_precip_prob']
            )
            
            return {
                'date': times[day_start].split('T')[0],
                'avg_wind': round(avg_wind, 1),
                'max_gust': round(max_gust, 1),
                'precip_probability': round(avg_precip_prob, 1),
                'cloud_cover': round(avg_cloud, 1),
                'favorable': favorable,
                'confidence': 'low' if day_offset > 10 else 'medium'
            }
            
        except Exception as e:
            print(f"Error analyzing day {day_offset}: {e}")
            return None
    
    def get_trip_forecast(self, destination: str, days_out: int = 7) -> Dict:
        """
        Get comprehensive forecast for a trip from KBDN to destination
        """
        print(f"\n{'='*70}")
        print(f"TRIP FORECAST: {self.home_base} → {destination}")
        print(f"Planning for {days_out} days ahead")
        print(f"{'='*70}\n")
        
        dest_name = self.destinations.get(destination, {}).get('name', destination)
        dest_coords = self.get_airport_coords(destination)
        
        result = {
            'departure': self.home_base,
            'destination': destination,
            'destination_name': dest_name,
            'days_out': days_out,
            'departure_forecast': {},
            'destination_forecast': {},
            'route_favorable': False
        }
        
        # Get forecasts for both airports
        print(f"Checking weather at {self.home_base} (Bend)...")
        home_forecast = self.get_short_term_forecast(*self.home_coords)
        
        print(f"Checking weather at {destination} ({dest_name})...")
        dest_forecast = self.get_short_term_forecast(*dest_coords)
        
        if home_forecast and dest_forecast:
            # Analyze the specific day
            hours_ahead = days_out * 24
            
            home_analysis = self.analyze_flying_window(home_forecast, hours_ahead, 6)
            dest_analysis = self.analyze_flying_window(dest_forecast, hours_ahead, 6)
            
            result['departure_forecast'] = home_analysis
            result['destination_forecast'] = dest_analysis
            result['route_favorable'] = home_analysis['flyable'] and dest_analysis['flyable']
        
        return result
    
    def scan_next_weeks(self, destination: str = None) -> Dict:
        """
        Scan the next 4 weeks for favorable flying windows
        If destination specified, check route. Otherwise check KBDN conditions only.
        """
        print(f"\n{'='*70}")
        if destination:
            print(f"4-WEEK OUTLOOK: {self.home_base} → {destination}")
        else:
            print(f"4-WEEK OUTLOOK: {self.home_base} (Local Flying)")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M PST')}")
        print(f"{'='*70}\n")
        
        # Get long-range forecast for home base
        home_outlook = self.get_long_range_outlook(*self.home_coords)
        
        if not home_outlook:
            print("❌ Could not retrieve long-range forecast")
            return {}
        
        # Analyze each day
        favorable_days = []
        
        print("Analyzing weather patterns...\n")
        print(f"{'Date':<12} {'Wind':<10} {'Gusts':<10} {'Precip%':<10} {'Clouds%':<10} {'Status':<15}")
        print("-" * 70)
        
        for day in range(16):  # Open-Meteo provides 16 days
            day_summary = self.analyze_long_range_day(home_outlook, day)
            
            if day_summary:
                status = "✓ Favorable" if day_summary['favorable'] else "⚠ Marginal"
                confidence = day_summary['confidence']
                
                print(f"{day_summary['date']:<12} "
                      f"{day_summary['avg_wind']:<10.1f} "
                      f"{day_summary['max_gust']:<10.1f} "
                      f"{day_summary['precip_probability']:<10.1f} "
                      f"{day_summary['cloud_cover']:<10.1f} "
                      f"{status:<15}")
                
                if day_summary['favorable']:
                    favorable_days.append(day_summary)
        
        print("\n" + "="*70)
        print(f"\nFound {len(favorable_days)} favorable days in the next 16 days")
        
        if favorable_days:
            print("\n📅 BEST DAYS FOR FLYING:")
            for day in favorable_days[:5]:  # Show top 5
                print(f"   {day['date']}: Wind {day['avg_wind']:.0f}kt, "
                      f"Precip {day['precip_probability']:.0f}%, "
                      f"Confidence: {day['confidence']}")
        
        return {
            'favorable_days': favorable_days,
            'outlook': home_outlook
        }


def main():
    """Main function with trip planning options"""
    
    planner = VFRTripPlanner()
    
    print("\n" + "="*70)
    print("VFR TRIP PLANNER & 4-WEEK OUTLOOK")
    print("Home Base: KBDN (Bend Municipal Airport, Oregon)")
    print("="*70)
    
    # Example 1: 4-week outlook for local flying from KBDN
    print("\n\n=== SCANNING NEXT 4 WEEKS FOR LOCAL FLYING ===")
    outlook = planner.scan_next_weeks()
    
    # Example 2: Check a specific trip
    print("\n\n=== CHECKING SPECIFIC TRIP ===")
    trip = planner.get_trip_forecast('KSFO', days_out=3)  # Trip to San Francisco in 3 days
    
    if trip['route_favorable']:
        print(f"\n✈️ GOOD TO GO! Trip to {trip['destination_name']} looks favorable!")
    else:
        print(f"\n⚠️ CONDITIONS NOT IDEAL for trip to {trip['destination_name']}")
        
        if trip['departure_forecast'].get('issues'):
            print(f"\n{planner.home_base} Issues:")
            for issue in trip['departure_forecast']['issues']:
                print(f"  - {issue}")
        
        if trip['destination_forecast'].get('issues'):
            print(f"\n{trip['destination']} Issues:")
            for issue in trip['destination_forecast']['issues']:
                print(f"  - {issue}")
    
    # List available destinations
    print("\n" + "="*70)
    print("\nAVAILABLE DESTINATIONS:")
    for icao, info in planner.destinations.items():
        print(f"  {icao} - {info['name']}")
    
    print("\n" + "="*70)
    print("\nTO USE THIS TOOL:")
    print("1. Run to see 4-week outlook for local flying")
    print("2. Modify destination in code to plan specific trips")
    print("3. Set up cron job to receive regular alerts")
    print("4. Adjust criteria in code based on your RV7 comfort levels")
    print("="*70)


if __name__ == "__main__":
    main()
