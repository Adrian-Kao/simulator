import os
import csv
import random
from datetime import datetime, timedelta

def generate_data():
    data_dir = '/Users/hayden/Documents/project/simulator/data/historical'
    os.makedirs(data_dir, exist_ok=True)
    out_file = os.path.join(data_dir, 'xinyi_historical_observations.csv')

    rng = random.Random(42)

    segments = [
        {'id': 'city_hall_road_eastbound', 'lanes': 3, 'speed_limit': 50, 'length': 500, 'type': 'other'},
        {'id': 'city_hall_road_westbound', 'lanes': 3, 'speed_limit': 50, 'length': 500, 'type': 'other'},
        {'id': 'xinyi_road_sec5_eastbound', 'lanes': 3, 'speed_limit': 50, 'length': 800, 'type': 'transit'},
        {'id': 'xinyi_road_sec5_westbound', 'lanes': 3, 'speed_limit': 50, 'length': 800, 'type': 'transit'},
        {'id': 'songren_road_northbound', 'lanes': 4, 'speed_limit': 50, 'length': 600, 'type': 'other'},
        {'id': 'songren_road_southbound', 'lanes': 4, 'speed_limit': 50, 'length': 600, 'type': 'other'},
        {'id': 'songshou_road_eastbound', 'lanes': 3, 'speed_limit': 40, 'length': 400, 'type': 'shopping'},
        {'id': 'songgao_road_eastbound', 'lanes': 3, 'speed_limit': 40, 'length': 350, 'type': 'shopping'},
        {'id': 'songzhi_road_northbound', 'lanes': 3, 'speed_limit': 40, 'length': 300, 'type': 'shopping'},
        {'id': 'zhongxiao_east_sec4_eastbound', 'lanes': 4, 'speed_limit': 50, 'length': 1000, 'type': 'transit'},
        {'id': 'zhongxiao_east_sec5_eastbound', 'lanes': 3, 'speed_limit': 50, 'length': 700, 'type': 'transit'},
        {'id': 'keelung_road_sec1_northbound', 'lanes': 3, 'speed_limit': 50, 'length': 800, 'type': 'transit'},
        {'id': 'keelung_road_sec1_southbound', 'lanes': 3, 'speed_limit': 50, 'length': 800, 'type': 'transit'},
        {'id': 'guangfu_south_road_northbound', 'lanes': 3, 'speed_limit': 50, 'length': 600, 'type': 'other'},
    ]

    start_date = datetime(2025, 8, 4)
    days = 28 # 4 weeks

    rows = []

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5
        day_type = 'weekend' if is_weekend else 'weekday'

        for hour in range(7, 23):
            for minute in range(0, 60, 5):
                dt = current_date.replace(hour=hour, minute=minute)
                ts_str = dt.isoformat()
                
                is_event = False
                if dt.date() == datetime(2025, 8, 9).date() and 17 <= hour < 22:
                    is_event = True
                elif dt.date() == datetime(2025, 8, 22).date() and 18 <= hour < 23:
                    is_event = True
                
                for seg in segments:
                    # Traffic Volume
                    if 7 <= hour < 7.5: period = 'am_shoulder'
                    elif 7.5 <= hour < 9.5: period = 'am_peak'
                    elif 9.5 <= hour < 12: period = 'midday'
                    elif 12 <= hour < 13.5: period = 'lunch'
                    elif 13.5 <= hour < 17: period = 'afternoon'
                    elif 17 <= hour < 19.5: period = 'pm_peak'
                    elif 19.5 <= hour < 21: period = 'pm_shoulder'
                    elif 21 <= hour < 23: period = 'evening'
                    else: period = 'off_peak'

                    if period == 'am_shoulder': base_vol = rng.uniform(250, 350)
                    elif period == 'am_peak': base_vol = rng.uniform(400, 550)
                    elif period == 'midday': base_vol = rng.uniform(250, 350)
                    elif period == 'lunch': base_vol = rng.uniform(300, 400)
                    elif period == 'afternoon': base_vol = rng.uniform(300, 400)
                    elif period == 'pm_peak': base_vol = rng.uniform(450, 600)
                    elif period == 'pm_shoulder': base_vol = rng.uniform(300, 400)
                    elif period == 'evening': base_vol = rng.uniform(150, 250)
                    else: base_vol = rng.uniform(50, 100)
                    
                    if seg['type'] in ('shopping', 'other'):
                        base_vol *= 0.7

                    if is_weekend:
                        if period in ('am_shoulder', 'am_peak'): base_vol *= 0.6
                        elif period in ('midday', 'lunch', 'afternoon'): base_vol *= 1.2
                        elif 18 <= hour:
                            base_vol *= 0.8 if 18 <= hour < 19.5 else 1.3
                        else:
                            base_vol *= 1.0
                    
                    vol = base_vol * seg['lanes']
                    vol *= rng.uniform(0.9, 1.1)

                    if is_event: vol *= 1.2
                    
                    capacity = seg['lanes'] * 900
                    vc_ratio = vol / capacity
                    speed = seg['speed_limit'] / (1 + 0.15 * (vc_ratio ** 4))
                    speed *= rng.uniform(0.95, 1.05)
                    speed = min(speed, seg['speed_limit'])

                    tt = (seg['length'] / 1000) / speed * 60
                    tt *= rng.uniform(0.95, 1.05)
                    
                    if seg['type'] == 'shopping':
                        if is_weekend:
                            if 11 <= hour < 21: ff = rng.uniform(5000, 8000)
                            else: ff = rng.uniform(1000, 2000)
                        else:
                            if (12 <= hour < 14) or (17 <= hour < 21): ff = rng.uniform(3000, 5000)
                            else: ff = rng.uniform(500, 1500)
                    elif seg['type'] == 'transit':
                        if is_weekend:
                            if (12 <= hour < 14) or (17 <= hour < 21): ff = rng.uniform(1500, 2500) * 0.8
                            else: ff = rng.uniform(300, 800) * 0.8
                        else:
                            if (12 <= hour < 14) or (17 <= hour < 21): ff = rng.uniform(1500, 2500)
                            else: ff = rng.uniform(300, 800)
                    else:
                        if is_weekend:
                            if (12 <= hour < 14) or (17 <= hour < 21): ff = rng.uniform(800, 1500) * 0.7
                            else: ff = rng.uniform(200, 500) * 0.7
                        else:
                            if (12 <= hour < 14) or (17 <= hour < 21): ff = rng.uniform(800, 1500)
                            else: ff = rng.uniform(200, 500)
                    
                    if is_event: ff *= 1.5

                    if is_weekend:
                        if 10 <= hour < 12: occ = rng.uniform(0.5, 0.7)
                        elif 12 <= hour < 20: occ = rng.uniform(0.9, 0.99)
                        else: occ = rng.uniform(0.6, 0.8)
                    else:
                        if 7 <= hour < 9: occ = rng.uniform(0.3, 0.5)
                        elif 9 <= hour < 12: occ = rng.uniform(0.6, 0.8)
                        elif 12 <= hour < 14: occ = rng.uniform(0.7, 0.9)
                        elif 14 <= hour < 17: occ = rng.uniform(0.7, 0.85)
                        elif 17 <= hour < 20: occ = rng.uniform(0.85, 0.98)
                        else: occ = rng.uniform(0.5, 0.7)
                        
                    if is_event: occ = min(1.0, occ + 0.05)
                    
                    if seg['type'] == 'transit':
                        if is_weekend:
                            b = rng.uniform(40, 70)
                            r = rng.uniform(40, 70)
                        else:
                            if 7 <= hour < 9:
                                b = rng.uniform(80, 120)
                                r = rng.uniform(20, 40)
                            elif 17 <= hour < 19.5:
                                b = rng.uniform(30, 50)
                                r = rng.uniform(90, 130)
                            else:
                                b = rng.uniform(15, 30)
                                r = rng.uniform(15, 30)
                    elif seg['type'] == 'shopping':
                        b = rng.uniform(20, 50)
                        r = rng.uniform(20, 50)
                        if is_weekend:
                            b *= 1.5
                            r *= 1.5
                    else:
                        b = rng.uniform(10, 25)
                        r = rng.uniform(10, 25)
                        
                    rows.append({
                        'timestamp': ts_str,
                        'day_type': day_type,
                        'segment_id': seg['id'],
                        'travel_time_minutes': round(tt, 2),
                        'travel_speed_kph': round(speed, 2),
                        'traffic_volume_vph': round(vol, 2),
                        'footfall_per_hour': round(ff, 2),
                        'parking_occupancy_rate': round(occ, 2),
                        'youbike_borrows': round(b, 2),
                        'youbike_returns': round(r, 2),
                        'event_flag': str(is_event).lower()
                    })
                    
    rows.sort(key=lambda x: (x['timestamp'], x['segment_id']))
    
    with open(out_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'day_type', 'segment_id', 'travel_time_minutes', 
            'travel_speed_kph', 'traffic_volume_vph', 'footfall_per_hour', 
            'parking_occupancy_rate', 'youbike_borrows', 'youbike_returns', 'event_flag'
        ])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Generated {len(rows)} rows.")
    for row in rows[:3]:
        print(row)

if __name__ == '__main__':
    generate_data()
