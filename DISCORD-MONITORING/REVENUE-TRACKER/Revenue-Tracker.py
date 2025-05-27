import requests
import json
import time
from datetime import datetime
import logging
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    filename='revenue_tracker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
DISCORD_WEBHOOK_URL = 'URL-WEBHOOK'
CHECK_INTERVAL = 3600  # 1 hour in seconds

# IDs to track
IDS_TO_TRACK = [
    'ID1',
    'ID2',
    'ID3'
]

def get_status_color(revenue_percentage):
    """Get color and emoji based on revenue percentage"""
    if revenue_percentage >= 100:
        return Fore.GREEN, "🟢"
    elif revenue_percentage >= 98:
        return Fore.YELLOW, "🟡"
    else:
        return Fore.RED, "🔴"

def get_auth_token():
    auth_url = 'https://api.qubic.li/Auth/Login'
    auth_body = {
        'userName': 'guest@qubic.li',
        'password': 'guest13@Qubic.li',
        'twoFactorCode': ''
    }
    auth_headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json-patch+json'
    }

    try:
        response = requests.post(auth_url, json=auth_body, headers=auth_headers, timeout=10)
        return response.json().get('token')
    except Exception as e:
        print(f"{Fore.RED}Auth error: {e}")
        return None

def send_discord_message(content):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={'content': content}, timeout=10)
    except Exception as e:
        print(f"{Fore.RED}Discord error: {e}")

def fetch_revenues(token):
    if not token:
        print(f"{Fore.RED}No token available")
        return

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    try:
        response = requests.get('https://api.qubic.li/Revenue/Get', headers=headers, timeout=10)
        data = response.json()
        
        # Network stats
        network_avg = data.get('averagePercentage', 0)
        created_at = data.get('createdAt', 'N/A')
        
        # Console output
        print(f"\n{Fore.CYAN}=== Network Statistics ===")
        print(f"Network Average: {network_avg:.1f}%")
        print(f"Created At: {created_at}")
        
        # Process IDs and calculate average
        total_revenue = 0
        active_ids = 0
        id_updates = []
        
        for revenue in data.get('revenues', []):
            if revenue['identity'] in IDS_TO_TRACK:
                id_short = revenue['identity'][:8]
                rev_percentage = revenue['revenuePercentage']
                total_revenue += rev_percentage
                active_ids += 1
                console_color, status_emoji = get_status_color(rev_percentage)
                
                # Console output - ID stats
                print(f"\n{Fore.WHITE}ID: {id_short}...")
                print(f"Index: {revenue['index']}")
                print(f"{console_color}Revenue: {rev_percentage:.1f}%")
                if revenue['isNewComputor']:
                    print(f"{Fore.YELLOW}New Computor: Yes ⭐")
                
                # Collect ID stats for Discord
                id_updates.append(
                    f"{status_emoji} `{id_short}...` | Index: {revenue['index']} | Revenue: **{rev_percentage:.1f}%**" +
                    (f" ⭐" if revenue['isNewComputor'] else "")
                )

        # Calculate your average
        your_avg = total_revenue / active_ids if active_ids > 0 else 0
        
        # Create Discord message
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        discord_message = [
            f"**Network Average** : {network_avg:.1f}%",
            f"**Your Average**    : {your_avg:.1f}%", 
            f"**Active IDs**      : {active_ids}",
            "▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔"
        ]
        
        # Add ID updates
        discord_message.extend(id_updates)
        
        # Add footer
        discord_message.extend([
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            f"*Updated: {time_str}*"
        ])
        
        # Send to Discord
        send_discord_message("\n".join(discord_message))
        print(f"\n{Fore.GREEN}Updates sent to Discord")

    except Exception as e:
        print(f"{Fore.RED}Error: {e}")

def main():
    print(f"{Fore.CYAN}Starting revenue tracker...")
    
    while True:
        try:
            token = get_auth_token()
            if token:
                fetch_revenues(token)
            print(f"\n{Fore.BLUE}Next update in {CHECK_INTERVAL/3600} hours...")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping...")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
