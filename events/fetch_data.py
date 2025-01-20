import requests
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
import csv

def format_date(date_str):
    return date_str.split('T')[0]

def poly_fetch_all():
    url = "https://gamma-api.polymarket.com/markets?limit=500&closed=false"
    headers = {"accept": "application/json"}

    r = []
    offset = 0
    
    for _ in range(64):
        # Construct the API request URL with the cursor if available
        request_url = f"{url}&offset={offset}"

        # Make the API request
        response = requests.get(request_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            return r
        
        data = response.json()

        # Collect titles from the current page
        # events = data.get("events", [])
        for event in data:
            rewards = event.get('clobRewards', [])
            r.append({
                "title": event["question"],
                "id": event["id"],
                "start": format_date(event["startDate"]),
                "end": format_date(event.get("endDate", "N/A")),
                "yes_price": event["bestAsk"],
                "no_price": round(1 - event.get("bestBid", 0), 3),
                "condition_id": event["conditionId"],
                "rewards_amount": rewards[0].get('rewardsAmount', 0) if rewards else 0,
                "rewards_daily_rate": rewards[0].get('rewardsDailyRate', 0) if rewards else 0,
                "rewards_min_size": event["rewardsMinSize"],
                "rewards_max_spread": event["rewardsMaxSpread"],
                "spread": event["spread"]
            })
        
        if data == []:
            break

        # Update the offset to the next page
        offset += 500

    return r

def print_data(data):
    i = 0
    for event in data:
        print(f"{i}\t{event['start']}\t{event['end']}\t{event['yes_price']}\t{event['no_price']}\t{event['title']}")
        i += 1

def save_data_to_csv(filename, data):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'id', 'start', 'end', 'yes_price', 'no_price', 'condition_id', 'rewards_amount', 'rewards_daily_rate', 'rewards_min_size', 'rewards_max_spread', 'spread']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
        writer.writeheader()
        writer.writerows(data)

def load_data_from_csv(filename):
    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        return [row for row in reader]
