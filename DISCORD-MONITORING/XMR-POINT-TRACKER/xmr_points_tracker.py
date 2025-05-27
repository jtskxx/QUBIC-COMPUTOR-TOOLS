import requests
import json
import time
from datetime import datetime
import logging
from colorama import Fore, Style, init
import statistics

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    filename='xmr_points_tracker.log',
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

def format_number(num):
    """Format large numbers with K/M suffix"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num:.0f}"

def get_rank_emoji(rank, total):
    """Get emoji based on rank"""
    percentage = (rank / total) * 100
    if percentage <= 10:
        return "🏆"  # Top 10%
    elif percentage <= 25:
        return "🥈"  # Top 25%
    elif percentage <= 50:
        return "🥉"  # Top 50%
    else:
        return "🔸"  # Rest

def get_performance_color(xmr_points, avg_points):
    """Get color and emoji based on performance vs average"""
    ratio = xmr_points / avg_points if avg_points > 0 else 0
    
    if ratio >= 1.5:
        return Fore.GREEN, "🟢"  # 150%+ of average
    elif ratio >= 1.0:
        return Fore.YELLOW, "🟡"  # 100-150% of average
    else:
        return Fore.RED, "🔴"  # Below average

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
        logging.error(f"Authentication failed: {e}")
        return None

def send_discord_message(content):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={'content': content}, timeout=10)
        logging.info("Discord message sent successfully")
    except Exception as e:
        print(f"{Fore.RED}Discord error: {e}")
        logging.error(f"Discord webhook failed: {e}")

def fetch_xmr_data(token):
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
        
        # Extract all revenues data
        all_revenues = data.get('revenues', [])
        
        # Calculate network statistics
        all_xmr_points = [r['xmrPoints'] for r in all_revenues if r['xmrPoints'] > 0]
        network_avg = statistics.mean(all_xmr_points) if all_xmr_points else 0
        network_median = statistics.median(all_xmr_points) if all_xmr_points else 0
        network_max = max(all_xmr_points) if all_xmr_points else 0
        
        # Sort all revenues by xmrPoints for ranking
        sorted_revenues = sorted(all_revenues, key=lambda x: x['xmrPoints'], reverse=True)
        
        # Create ranking dictionary
        rankings = {r['identity']: idx + 1 for idx, r in enumerate(sorted_revenues)}
        
        # Console output - Network Stats
        print(f"\n{Fore.CYAN}=== XMR Points Network Statistics ===")
        print(f"Total Computors: {len(all_revenues)}")
        print(f"Network Average: {format_number(network_avg)}")
        print(f"Network Median: {format_number(network_median)}")
        print(f"Network Max: {format_number(network_max)}")
        
        # Process tracked IDs
        tracked_data = []
        total_xmr_points = 0
        active_ids = 0
        id_updates = []
        
        for revenue in all_revenues:
            if revenue['identity'] in IDS_TO_TRACK:
                id_short = revenue['identity'][:8]
                xmr_points = revenue['xmrPoints']
                rank = rankings[revenue['identity']]
                total_xmr_points += xmr_points
                active_ids += 1
                
                console_color, status_emoji = get_performance_color(xmr_points, network_avg)
                rank_emoji = get_rank_emoji(rank, len(all_revenues))
                
                # Store for later sorting
                tracked_data.append({
                    'id_short': id_short,
                    'identity': revenue['identity'],
                    'index': revenue['index'],
                    'xmr_points': xmr_points,
                    'rank': rank,
                    'revenue_percentage': revenue['revenuePercentage'],
                    'is_new': revenue['isNewComputor'],
                    'console_color': console_color,
                    'status_emoji': status_emoji,
                    'rank_emoji': rank_emoji
                })
                
                # Console output - ID stats
                print(f"\n{Fore.WHITE}ID: {id_short}...")
                print(f"Index: {revenue['index']}")
                print(f"{console_color}XMR Points: {format_number(xmr_points)} ({xmr_points:.0f})")
                print(f"Rank: #{rank}/{len(all_revenues)} {rank_emoji}")
                print(f"Revenue: {revenue['revenuePercentage']:.1f}%")
                if revenue['isNewComputor']:
                    print(f"{Fore.YELLOW}New Computor: Yes ⭐")
        
        # Sort tracked IDs by rank
        tracked_data.sort(key=lambda x: x['rank'])
        
        # Calculate your average
        your_avg = total_xmr_points / active_ids if active_ids > 0 else 0
        
        # Prepare Discord message
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        discord_message = [
            "**📊 XMR Points Tracker Report**",
            "▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔",
            f"**Network Stats:**",
            f"• Total Computors: **{len(all_revenues)}**",
            f"• Network Average: **{format_number(network_avg)}**",
            f"• Network Median: **{format_number(network_median)}**",
            f"• Network Max: **{format_number(network_max)}**",
            "",
            f"**Your Stats:**",
            f"• Your Average: **{format_number(your_avg)}** ({(your_avg/network_avg*100):.1f}% of network avg)",
            f"• Active IDs: **{active_ids}**",
            f"• Total XMR Points: **{format_number(total_xmr_points)}**",
            "▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔",
            "**Your IDs (sorted by rank):**"
        ]
        
        # Add sorted ID updates to Discord message
        for data in tracked_data:
            perf_vs_avg = (data['xmr_points'] / network_avg * 100) if network_avg > 0 else 0
            update_str = (
                f"{data['rank_emoji']} **#{data['rank']}** {data['status_emoji']} `{data['id_short']}...` | "
                f"Index: **{data['index']}** | XMR: **{format_number(data['xmr_points'])}** "
                f"({perf_vs_avg:.0f}% of avg) | Rev: **{data['revenue_percentage']:.1f}%**"
            )
            if data['is_new']:
                update_str += " ⭐"
            discord_message.append(update_str)
        
        # Add footer
        discord_message.extend([
            "▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁",
            f"*Updated: {time_str}*"
        ])
        
        # Send to Discord
        send_discord_message("\n".join(discord_message))
        print(f"\n{Fore.GREEN}Updates sent to Discord")
        
        # Log summary
        logging.info(f"Update completed - Network Avg: {network_avg:.0f}, Your Avg: {your_avg:.0f}, Active IDs: {active_ids}")

    except Exception as e:
        print(f"{Fore.RED}Error fetching data: {e}")
        logging.error(f"Data fetch error: {e}")

def main():
    print(f"{Fore.CYAN}Starting XMR Points tracker...")
    print(f"{Fore.YELLOW}Tracking {len(IDS_TO_TRACK)} IDs")
    
    while True:
        try:
            token = get_auth_token()
            if token:
                fetch_xmr_data(token)
            print(f"\n{Fore.BLUE}Next update in {CHECK_INTERVAL/3600} hours...")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping tracker...")
            break
        except Exception as e:
            print(f"{Fore.RED}Unexpected error: {e}")
            logging.error(f"Main loop error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    main()
