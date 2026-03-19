#!/usr/bin/env python3
"""
Interactive VFR Trip Planner
Allows you to check specific dates and destinations interactively
"""

import sys
from datetime import datetime, timedelta
from vfr_trip_planner import VFRTripPlanner

def print_menu():
    """Display the main menu"""
    print("\n" + "="*70)
    print("VFR TRIP PLANNER - Interactive Mode")
    print("Home Base: KBDN (Bend Municipal Airport)")
    print("="*70)
    print("\n1. View 4-week outlook for local flying")
    print("2. Check specific trip forecast")
    print("3. Find best flying days in next 2 weeks")
    print("4. Check weather for multiple destinations")
    print("5. Exit")
    print()

def find_best_days(planner):
    """Find and display the best flying days"""
    print("\nScanning for favorable flying conditions...")
    outlook = planner.scan_next_weeks()
    
    favorable = outlook.get('favorable_days', [])
    
    if not favorable:
        print("\n⚠️ No clearly favorable days found in forecast period")
        print("Note: Long-range forecasts have lower confidence")
    else:
        print(f"\n✈️ Found {len(favorable)} favorable day(s)!")
        print("\nBest opportunities for VFR flight:")
        print("-" * 70)
        
        for i, day in enumerate(favorable[:10], 1):
            date_obj = datetime.strptime(day['date'], '%Y-%m-%d')
            days_from_now = (date_obj - datetime.now()).days
            
            print(f"\n{i}. {day['date']} ({days_from_now} days from now)")
            print(f"   Wind: {day['avg_wind']:.0f} kt (gusts to {day['max_gust']:.0f} kt)")
            print(f"   Precipitation chance: {day['precip_probability']:.0f}%")
            print(f"   Cloud cover: {day['cloud_cover']:.0f}%")
            print(f"   Confidence: {day['confidence'].upper()}")

def check_specific_trip(planner):
    """Check weather for a specific trip"""
    print("\nAvailable destinations:")
    destinations = list(planner.destinations.keys())
    for i, icao in enumerate(destinations, 1):
        name = planner.destinations[icao]['name']
        print(f"  {i}. {icao} - {name}")
    
    print(f"\n  Or enter custom ICAO code")
    
    dest_input = input("\nSelect destination (number or ICAO code): ").strip().upper()
    
    # Handle numeric selection
    if dest_input.isdigit():
        idx = int(dest_input) - 1
        if 0 <= idx < len(destinations):
            destination = destinations[idx]
        else:
            print("Invalid selection")
            return
    else:
        destination = dest_input
    
    # Get number of days out
    try:
        days_out = int(input("How many days from now? (0-7): ").strip())
        if days_out < 0 or days_out > 7:
            print("Please enter a number between 0 and 7")
            return
    except ValueError:
        print("Invalid number")
        return
    
    # Get the forecast
    trip = planner.get_trip_forecast(destination, days_out)
    
    # Display results
    print("\n" + "="*70)
    if trip['route_favorable']:
        print("✈️ TRIP LOOKS GOOD!")
        print(f"\nConditions favorable for {planner.home_base} → {destination}")
        print(f"Planning date: {(datetime.now() + timedelta(days=days_out)).strftime('%Y-%m-%d')}")
    else:
        print("⚠️ MARGINAL OR UNFAVORABLE CONDITIONS")
        print(f"\nTrip: {planner.home_base} → {destination}")
        print(f"Date: {(datetime.now() + timedelta(days=days_out)).strftime('%Y-%m-%d')}")
        
        print("\nIssues detected:")
        if trip['departure_forecast'].get('issues'):
            print(f"\nAt {planner.home_base}:")
            for issue in trip['departure_forecast']['issues']:
                print(f"  • {issue}")
        
        if trip['destination_forecast'].get('issues'):
            print(f"\nAt {destination}:")
            for issue in trip['destination_forecast']['issues']:
                print(f"  • {issue}")
    
    print("="*70)
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("• Always check NOTAMs before departure")
    print("• Verify winds aloft and turbulence forecasts")
    print("• Check density altitude, especially in summer")
    print("• Monitor weather closer to departure date")
    print("• Consider alternate airports along route")

def check_multiple_destinations(planner):
    """Check weather for all configured destinations"""
    days_out = int(input("\nHow many days from now? (0-7): ").strip())
    
    if days_out < 0 or days_out > 7:
        print("Please enter a number between 0 and 7")
        return
    
    print(f"\n{'='*70}")
    print(f"WEATHER CHECK FOR ALL DESTINATIONS")
    print(f"Date: {(datetime.now() + timedelta(days=days_out)).strftime('%Y-%m-%d')}")
    print(f"{'='*70}\n")
    
    results = []
    
    for icao, info in planner.destinations.items():
        print(f"Checking {icao} ({info['name']})...", end=' ')
        trip = planner.get_trip_forecast(icao, days_out)
        
        if trip['route_favorable']:
            print("✓ Good")
            results.append((icao, info['name'], True, trip))
        else:
            print("⚠ Marginal")
            results.append((icao, info['name'], False, trip))
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")
    
    good_destinations = [r for r in results if r[2]]
    
    if good_destinations:
        print(f"✈️ {len(good_destinations)} destination(s) with favorable conditions:\n")
        for icao, name, _, _ in good_destinations:
            print(f"   • {icao} - {name}")
    else:
        print("⚠️ No destinations currently showing favorable conditions")
        print("Consider waiting for better weather or checking longer-range outlook")

def main():
    """Main interactive loop"""
    planner = VFRTripPlanner()
    
    while True:
        print_menu()
        
        try:
            choice = input("Select option (1-5): ").strip()
            
            if choice == '1':
                planner.scan_next_weeks()
                
            elif choice == '2':
                check_specific_trip(planner)
                
            elif choice == '3':
                find_best_days(planner)
                
            elif choice == '4':
                check_multiple_destinations(planner)
                
            elif choice == '5':
                print("\nBlue skies and tailwinds! ✈️\n")
                sys.exit(0)
                
            else:
                print("\n❌ Invalid option. Please select 1-5.")
            
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\n\nExiting... Blue skies! ✈️\n")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
