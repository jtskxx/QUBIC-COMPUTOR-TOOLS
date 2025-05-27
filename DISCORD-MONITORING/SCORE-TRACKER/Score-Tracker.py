import requests
import json
import time
from datetime import datetime, timedelta, timezone
from colorama import Fore, Style, init
import logging
import sys
from PIL import Image, ImageDraw, ImageFont
import io
from io import StringIO

init(autoreset=True)
logging.basicConfig(filename='fetch_scores.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Discord webhook URL
WEBHOOK_URL = "URL-WEBHOOK"

# Your IDs
YOUR_IDS = [
    'ID1',
    'ID2',
    'ID3'
]

# Add global variables for idle detection
last_total_score = None
last_score_change_time = None
IDLE_THRESHOLD = 25 * 60  # 25 minutes in seconds

def create_image(text):
    # Set up image parameters
    font_size = 16
    padding = 20
    line_height = font_size + 8
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_size)
        except:
            font = ImageFont.load_default()

    # Split text into lines and measure dimensions
    lines = text.split('\n')
    max_width = max(font.getlength(line) for line in lines) + padding * 2
    total_height = len(lines) * line_height + padding * 2

    # Create image
    img = Image.new('RGB', (int(max_width), total_height), color='black')
    draw = ImageDraw.Draw(img)

    # Color mapping
    color_map = {
        Fore.CYAN: (0, 255, 255),
        Fore.YELLOW: (255, 255, 0),
        Fore.RED: (255, 0, 0),
        Fore.GREEN: (0, 255, 0),
        Fore.BLUE: (0, 100, 255),
        Fore.MAGENTA: (255, 0, 255),
        Fore.LIGHTMAGENTA_EX: (255, 100, 255),
        Fore.LIGHTCYAN_EX: (100, 255, 255),
        Fore.LIGHTYELLOW_EX: (255, 255, 100),
        Fore.WHITE: (255, 255, 255),
        Fore.LIGHTGREEN_EX: (100, 255, 100),
        Fore.LIGHTBLUE_EX: (100, 100, 255)
    }

    # Draw text with colors
    y = padding
    current_color = (255, 255, 255)  # Default color

    for line in lines:
        if not line.strip():  # Handle empty lines
            y += line_height
            continue

        x = padding
        
        # Check for color codes in line
        for color, rgb in color_map.items():
            if color in line:
                current_color = rgb
                line = line.replace(color, '')
        
        # Remove any remaining ANSI codes
        line = line.replace(Style.BRIGHT, '').replace(Style.RESET_ALL, '')
        draw.text((x, y), line, font=font, fill=current_color)
        y += line_height

    return img

def send_discord_message(output_buffer):
    img = create_image(output_buffer.getvalue())
    
    # Convert image to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    files = {'file': ('qubic_status.png', img_byte_arr, 'image/png')}
    try:
        response = requests.post(WEBHOOK_URL, files=files)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Discord message: {e}")
        logging.error(f"Failed to send Discord message: {e}")

def get_epoch_times():
    now = datetime.now(timezone.utc)
    days_since_wednesday = (now.weekday() - 2) % 7 
    epoch_start = datetime(now.year, now.month, now.day, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=days_since_wednesday)
    
    if now < epoch_start:
        epoch_start -= timedelta(days=7)

    epoch_end = epoch_start + timedelta(days=7)
    
    return epoch_start, epoch_end

def check_idle_status(current_total_score):
    global last_total_score, last_score_change_time
    current_time = time.time()
    
    if last_total_score is None:
        last_total_score = current_total_score
        last_score_change_time = current_time
        return True  # Start as idle
    
    if current_total_score != last_total_score:
        last_total_score = current_total_score
        last_score_change_time = current_time
        return False  # Not idle when score changes
    
    idle_time = current_time - last_score_change_time
    return idle_time >= IDLE_THRESHOLD

def calculate_projected_avg(total_score, current_rate_per_hour, epoch_start, epoch_end, final_total_ids=676):
    now = datetime.now(timezone.utc)
    time_left_hours = (epoch_end - now).total_seconds() / 3600
    projected_score_increase = current_rate_per_hour * time_left_hours
    final_total_score = total_score + projected_score_increase
    projected_avg = final_total_score / final_total_ids
    return projected_avg, time_left_hours

def calculate_safe_id_count(active_ids, network_average_score, total_ids=676):
    if not active_ids:
        return {}
    
    total_score = sum(score for _, _, score, _ in active_ids)
    possible_ids = int(total_score / network_average_score)
    
    recommendations = {
        "Conservative (Safe)": possible_ids,
        "Moderate": possible_ids if total_score < (possible_ids + 1) * network_average_score + 20 else possible_ids + 1,
        "Aggressive": possible_ids if total_score < (possible_ids + 1) * network_average_score else possible_ids + 1
    }
    
    return recommendations

def calculate_new_id_potential(total_your_score, average_score, your_total_rate):
    potential_ids = total_your_score / average_score
    whole_ids = int(potential_ids)
    partial_progress = potential_ids - whole_ids
    solutions_needed = (1 - partial_progress) * average_score
    estimated_hours = solutions_needed / your_total_rate if your_total_rate > 0 else float('inf')
    return whole_ids, partial_progress, solutions_needed, estimated_hours

def fetch_scores():
    output_buffer = StringIO()
    original_stdout = sys.stdout
    sys.stdout = output_buffer
    
    try:
        rBody = {'userName': 'guest@qubic.li', 'password': 'guest13@Qubic.li', 'twoFactorCode': ''}
        rHeaders = {'Accept': 'application/json', 'Content-Type': 'application/json-patch+json'}

        r = requests.post('https://api.qubic.li/Auth/Login', data=json.dumps(rBody), headers=rHeaders, timeout=10)
        r.raise_for_status()
        token = r.json().get('token')
        
        if token:
            rHeaders = {'Accept': 'application/json', 'Authorization': 'Bearer ' + token}
            
            r = requests.get('https://api.qubic.li/Score/Get', headers=rHeaders, timeout=10)
            r.raise_for_status()
            networkStat = r.json()
            
            current_solution_rate = networkStat.get('solutionsPerHourCalculated', 0)  
            current_rate_per_hour = current_solution_rate
            
            scores = networkStat.get('scores', [])
            s = sorted(scores, key=lambda t: t['score'], reverse=True)

            rank = 1
            total_ids = len(s)
            
            computors_count = sum(1 for comp in s if comp.get('isComputor', False))
            candidates_count = sum(1 for comp in s if not comp.get('isComputor', False))

            total_score = sum(comp['adminScore'] for comp in s if 'adminScore' in comp)
            
            # Check idle status
            is_idle = check_idle_status(total_score)
            idle_status = f"{Fore.GREEN}ON" if is_idle else f"{Fore.RED}OFF"

            max_score = max(comp['score'] for comp in s) if s else 0
            average_score = sum(comp['score'] for comp in s) / total_ids if total_ids > 0 else 0

            epoch_start, epoch_end = get_epoch_times()
            now = datetime.now(timezone.utc)
            time_elapsed = (now - epoch_start).total_seconds() / 3600
            time_left_hours = (epoch_end - now).total_seconds() / 3600

            projected_avg, _ = calculate_projected_avg(
                total_score, current_rate_per_hour, epoch_start, epoch_end, final_total_ids=676
            )

            logging.info(f"Total Score: {total_score}, Current Solution Rate: {current_rate_per_hour}, Projected Average: {projected_avg}")
            
            your_active_ids = []
            
            # ASCII Art and initial information
            print(Fore.CYAN + Style.BRIGHT + r"""                            

     ▄█    ▄████████     ███        ▄████████    ▄█   ▄█▄  ▄█          ▄███████▄  ▄██████▄   ▄██████▄   ▄█       
    ███   ███    ███ ▀█████████▄   ███    ███   ███ ▄███▀ ███         ███    ███ ███    ███ ███    ███ ███       
    ███   ███    █▀     ▀███▀▀██   ███    █▀    ███▐██▀   ███▌        ███    ███ ███    ███ ███    ███ ███       
    ███  ▄███▄▄▄         ███   ▀   ███         ▄█████▀    ███▌        ███    ███ ███    ███ ███    ███ ███       
    ███ ▀▀███▀▀▀         ███     ▀███████████ ▀▀█████▄    ███▌      ▀█████████▀  ███    ███ ███    ███ ███       
    ███   ███    █▄      ███              ███   ███▐██▄   ███         ███        ███    ███ ███    ███ ███       
    ███   ███    ███     ███        ▄█    ███   ███ ▀███▄ ███         ███        ███    ███ ███    ███ ███▌    ▄ 
█▄ ▄███   ██████████    ▄████▀    ▄████████▀    ███   ▀█▀ █▀         ▄████▀       ▀██████▀   ▀██████▀  █████▄▄██ 
▀▀▀▀▀▀                                          ▀                                                      ▀             
                          
            """ + "="*60)
            
            print(Fore.YELLOW + f"\nCurrent Network Solution Rate: {current_rate_per_hour:.2f}/hour")
            print(Fore.YELLOW + f"Time Left in Epoch: {time_left_hours:.2f} hours")
            print(Fore.YELLOW + f"Time Elapsed in Epoch: {time_elapsed:.2f} hours")
            print(Fore.YELLOW + f"Estimated Solution Rate for 1 ID: {current_rate_per_hour / 676:.2f}/hour")
            print(Fore.WHITE + f"IDLE: {idle_status}\n")
            
            print(Fore.CYAN + "Your Active IDs Performance:")
            for comp in s:
                if comp['identity'] in YOUR_IDS and comp['score'] > 0:
                    score = comp['score']
                    rate = score / time_elapsed if time_elapsed > 0 else 0
                    
                    if rank > 450:
                        color = Fore.RED + Style.BRIGHT
                        danger_message = Fore.RED + Style.BRIGHT + "DANGER! LOW RANK"
                    elif rank > 250:
                        color = Fore.LIGHTYELLOW_EX + Style.BRIGHT
                        danger_message = Fore.YELLOW + "Moderate Rank"
                    else:
                        color = Fore.GREEN + Style.BRIGHT
                        danger_message = Fore.GREEN + "Healthy Rank"

                    print(color + f"ID: {Fore.LIGHTCYAN_EX}{comp['identity']}")
                    print(f"Rank: {rank} | Score: {score} | {danger_message}")
                    print(f"Computor Status: {'Yes' if comp.get('isComputor', False) else 'No'}")
                    print(f"Estimated Solution Rate: {rate:.2f}/h")
                    print(Fore.BLUE + "-"*60)
                    
                    your_active_ids.append((comp['identity'], rank, score, rate))

                rank += 1

            if your_active_ids:
                active_ranks = [rank for _, rank, _, _ in your_active_ids]
                print(Fore.CYAN + "\nActive IDs Analysis:")
                print(f"Total Active IDs: {len(your_active_ids)}")
                print(f"Best Rank: {min(active_ranks)}")
                print(f"Worst Rank: {max(active_ranks)}")
                print(f"Average Rank: {sum(active_ranks) / len(active_ranks):.0f}")
                
                total_your_score = sum(score for _, _, score, _ in your_active_ids)
                avg_your_score = total_your_score / len(your_active_ids)
                your_total_rate = sum(rate for _, _, _, rate in your_active_ids)
                
                print(f"Total Score: {total_your_score}")
                print(f"Average Score: {avg_your_score:.2f}")
                print(f"Your Total Solution Rate: {your_total_rate:.2f}/h")
                
                # New ID potential analysis
                whole_ids, partial_progress, solutions_needed, time_to_next = calculate_new_id_potential(
                    total_your_score, 
                    average_score,
                    your_total_rate
                )
                
                print(Fore.LIGHTGREEN_EX + "\nNew ID Potential Analysis:")
                print(f"Your Total Score / Network Average: {total_your_score / average_score:.2f}")
                print(f"Your Total Score / Network 676 Comps.: {total_your_score / (total_score / 676):.2f}")
                print(f"Complete IDs Possible: {whole_ids}")
                print(f"Progress towards next ID: {partial_progress:.2%}")
                print(f"Solutions needed for next ID: {solutions_needed:.2f}")
                if time_to_next == float('inf'):
                    print(f"Estimated time for next ID: N/A (No solutions yet)")
                else:
                    print(f"Estimated time for next ID at your rate: {time_to_next:.2f} hours")
                
                safe_id_counts = calculate_safe_id_count(your_active_ids, average_score)
                
                print(Fore.MAGENTA + "\nRecommended number of IDs to run:")
                for strategy, count in safe_id_counts.items():
                    if strategy == "Conservative (Safe)":
                        print(Fore.GREEN + f"{strategy}: {count} IDs")
                    elif strategy == "Moderate":
                        print(Fore.YELLOW + f"{strategy}: {count} IDs")
                    else:
                        print(Fore.RED + f"{strategy}: {count} IDs")

            print(Fore.CYAN + f"\nNetwork Statistics:")
            print(Fore.CYAN + f"Total IDs: {total_ids}")
            print(Fore.GREEN + f"Computors: {computors_count}")
            print(Fore.YELLOW + f"Candidates: {candidates_count}")
            print(Fore.MAGENTA + f"Maximum Score: {max_score}")
            print(Fore.LIGHTMAGENTA_EX + f"Average Score: {average_score:.2f}")
            print(Fore.LIGHTMAGENTA_EX + f"Projected Average: {projected_avg:.2f}")
            print(Fore.LIGHTMAGENTA_EX + f"Current Solution Rate: {current_rate_per_hour:.2f}/h")
            print(Fore.LIGHTMAGENTA_EX + f"Time Left in Epoch (hours): {time_left_hours:.2f}")
            print(Fore.LIGHTMAGENTA_EX + f"Total Score: {total_score}")
            
            if your_active_ids:
                your_total_rate = sum(rate for _, _, _, rate in your_active_ids)
                print(Fore.GREEN + f"\nYour Total Estimated Solution Rate: {your_total_rate:.2f}/hour")
            
            print(Fore.BLUE + "="*60)

        else:
            logging.error("Authentication failed. No token received.")
            print(Fore.RED + "Authentication failed. No token received.")

    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout error during authentication: {errt}")
        print(Fore.RED + 'Time out Error:', errt)
    except requests.exceptions.RequestException as err:
        logging.error(f"API error: {err}")
        print(Fore.RED + "API error:", err)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(Fore.RED + f"Unexpected error: {e}")
    
    finally:
        sys.stdout = original_stdout
        send_discord_message(output_buffer)
        output_buffer.close()

def main():
    print("Starting Qubic Monitor with Discord webhook integration...")
    while True:
        try:
            fetch_scores()
            print(Fore.LIGHTBLUE_EX + "\nNext update in 60 minutes... ⏳\n" + "="*60)
            time.sleep(3600)  # 60 minutes
        except KeyboardInterrupt:
            print(Fore.RED + "Process interrupted. Exiting...")
            logging.info("Process interrupted by user.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            print(Fore.RED + f"An error occurred: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()
