import os
import json
import pandas as pd
from stravalib.client import Client

DATA_DIR = 'data'
ACTIVITIES_FILE = os.path.join(DATA_DIR, 'activities.csv')

def get_client():
    client = Client()
    refresh_response = client.refresh_access_token(
        client_id=os.environ['STRAVA_CLIENT_ID'],
        client_secret=os.environ['STRAVA_CLIENT_SECRET'],
        refresh_token=os.environ['STRAVA_REFRESH_TOKEN']
    )
    client.access_token = refresh_response['access_token']
    return client

def get_safe_value(obj):
    if obj is None: return 0
    if hasattr(obj, 'total_seconds'): return obj.total_seconds()
    if hasattr(obj, 'magnitude'): return obj.magnitude
    if hasattr(obj, 'num'): return obj.num
    if hasattr(obj, 'seconds'): return obj.seconds
    return float(obj)

def update_activities():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("🚀 --- HARD RESET START ---")
    
    if os.path.exists(ACTIVITIES_FILE):
        os.remove(ACTIVITIES_FILE)
    
    client = get_client()
    new_activities = []
    
    print("⏳ Downloading data...")
    
    activity_generator = client.get_activities(limit=None)
    
    count = 0
    try:
        for act in activity_generator:
            try:
                data = {
                    'id': act.id,
                    'name': act.name,
                    'start_date': act.start_date_local,
                    'distance_km': get_safe_value(act.distance) / 1000, 
                    'moving_time_min': get_safe_value(act.moving_time) / 60,
                    'elapsed_time': get_safe_value(act.elapsed_time) / 60,
                    'elevation_m': get_safe_value(act.total_elevation_gain),
                    'type': act.type,
                    'average_speed_kmh': get_safe_value(act.average_speed) * 3.6,
                    'max_speed': get_safe_value(act.max_speed),
                    'pr_count': act.pr_count,
                    'kudos': act.kudos_count,
                    'kilojoules': get_safe_value(getattr(act, 'kilojoules', 0)),
                    'average_heartrate': get_safe_value(getattr(act, 'average_heartrate', 0)),
                    'max_heartrate': get_safe_value(getattr(act, 'max_heartrate', 0))
                }
                new_activities.append(data)
                count += 1
                
                if count % 50 == 0:
                    print(f"✅ Processed: {count}...")
                    
            except Exception as inner_e:
                print(f"❌ Error at ID ({act.id}): {inner_e}")
                continue
                
    except Exception as e:
        print(f"🔥 CRITICAL ERROR: {e}")
    
    print(f"🏁 Total downloaded: {count}")

    if new_activities:
        final_df = pd.DataFrame(new_activities)
        final_df['start_date'] = pd.to_datetime(final_df['start_date'])
        final_df = final_df.sort_values('start_date', ascending=False)
        
        final_df.to_csv(ACTIVITIES_FILE, index=False)
        print(f"💾 Saved. Rows: {len(final_df)}")
        return final_df
    else:
        print("⚠️ Empty response. Creating empty file.")
        empty = pd.DataFrame(columns=['id', 'name', 'start_date', 'distance_km'])
        empty.to_csv(ACTIVITIES_FILE, index=False)
        return empty

if __name__ == "__main__":
    update_activities()
