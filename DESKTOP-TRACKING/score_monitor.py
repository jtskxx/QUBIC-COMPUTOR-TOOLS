import requests
import json
import time
from datetime import datetime, timedelta, timezone
from colorama import Fore, Style, init
import logging
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich.align import Align
from rich import box

init(autoreset=True)
logging.basicConfig(filename='fetch_scores.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Your IDs
YOUR_IDS = [
    'ID1',
    'ID2',
    'ID3'
]

# Initialize Rich console
console = Console()

def get_epoch_times():
    now = datetime.now(timezone.utc)
    days_since_wednesday = (now.weekday() - 2) % 7 
    epoch_start = datetime(now.year, now.month, now.day, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=days_since_wednesday)
    
    if now < epoch_start:
        epoch_start -= timedelta(days=7)

    epoch_end = epoch_start + timedelta(days=7)
    
    return epoch_start, epoch_end

def calculate_projected_avg(total_score, current_rate_per_hour, epoch_start, epoch_end, final_total_ids=676):
    now = datetime.now(timezone.utc)
    time_left_hours = max(0.001, (epoch_end - now).total_seconds() / 3600)  # Protect against zero or negative
    projected_score_increase = current_rate_per_hour * time_left_hours
    final_total_score = total_score + projected_score_increase
    
    # Protect against zero division
    if final_total_ids <= 0:
        final_total_ids = 676  # Fallback to default value
        
    projected_avg = final_total_score / final_total_ids
    return projected_avg, time_left_hours

def calculate_safe_id_count(active_ids, theoretical_perfect_score, total_ids=676):
    if not active_ids:
        return {}
    
    total_score = sum(score for _, _, score, _ in active_ids)
    score_vs_perfect = total_score / theoretical_perfect_score if theoretical_perfect_score > 0 else 0
    possible_ids = int(score_vs_perfect)
    
    recommendations = {
        "Conservative (Safe)": possible_ids,
        "Moderate": possible_ids if score_vs_perfect < (possible_ids + 1) + 0.1 else possible_ids + 1,
        "Aggressive": possible_ids if score_vs_perfect < (possible_ids + 1) else possible_ids + 1
    }
    
    return recommendations

def calculate_new_id_potential(total_your_score, your_total_rate, total_network_score):
    # Protect against division by zero
    theoretical_perfect_score = total_network_score / 676 if total_network_score > 0 else 0.001
    
    # Protect against zero theoretical_perfect_score
    if theoretical_perfect_score <= 0:
        theoretical_perfect_score = 0.001  # Small non-zero value to avoid division by zero
        
    score_vs_perfect = total_your_score / theoretical_perfect_score if theoretical_perfect_score > 0 else 0
    
    whole_ids = int(score_vs_perfect)
    partial_progress = score_vs_perfect - whole_ids
    solutions_needed = (1 - partial_progress) * theoretical_perfect_score
    
    # Protect against division by zero for estimated_hours
    if your_total_rate > 0:
        estimated_hours = solutions_needed / your_total_rate
    else:
        estimated_hours = float('inf')
    
    return whole_ids, partial_progress, solutions_needed, estimated_hours, score_vs_perfect, theoretical_perfect_score

def create_progress_bar(progress, total_width=30, color_theme="blue"):
    progress_ratio = min(1.0, max(0.0, progress))
    
    # Color themes based on the parameter
    if color_theme == "blue":
        style = "blue"
        complete_style = "bright_blue"
    elif color_theme == "green":
        style = "green"
        complete_style = "bright_green"
    elif color_theme == "yellow":
        style = "yellow"
        complete_style = "bright_yellow"
    elif color_theme == "red":
        style = "red"
        complete_style = "bright_red"
    else:
        style = "blue"
        complete_style = "bright_blue"
    
    return Text(f"{'━' * int(progress_ratio * total_width)}{'╺' if 0 < progress_ratio < 1 else ''}{'━' * int((1 - progress_ratio) * total_width)} {progress_ratio:.2%}", style=complete_style)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_scores():
    clear_screen()
    console.print("")
    
    # Create the logo with a bolder color
    logo = """
     ▄█    ▄████████     ███        ▄████████    ▄█   ▄█▄  ▄█          ▄███████▄  ▄██████▄   ▄██████▄   ▄█       
    ███   ███    ███ ▀█████████▄   ███    ███   ███ ▄███▀ ███         ███    ███ ███    ███ ███    ███ ███       
    ███   ███    █▀     ▀███▀▀██   ███    █▀    ███▐██▀   ███▌        ███    ███ ███    ███ ███    ███ ███       
    ███  ▄███▄▄▄         ███   ▀   ███         ▄█████▀    ███▌        ███    ███ ███    ███ ███    ███ ███       
    ███ ▀▀███▀▀▀         ███     ▀███████████ ▀▀█████▄    ███▌      ▀█████████▀  ███    ███ ███    ███ ███       
    ███   ███    █▄      ███              ███   ███▐██▄   ███         ███        ███    ███ ███    ███ ███       
    ███   ███    ███     ███        ▄█    ███   ███ ▀███▄ ███         ███        ███    ███ ███    ███ ███▌    ▄ 
█▄ ▄███   ██████████    ▄████▀    ▄████████▀    ███   ▀█▀ █▀         ▄████▀       ▀██████▀   ▀██████▀  █████▄▄██ 
▀▀▀▀▀▀                                          ▀                                                      ▀         
    """
    
    console.print(Align.center(Text(logo, style="gold1")))
    console.print("")
    
    # Authentication headers
    rBody = {'userName': 'guest@qubic.li', 'password': 'guest13@Qubic.li', 'twoFactorCode': ''}
    rHeaders = {'Accept': 'application/json', 'Content-Type': 'application/json-patch+json'}

    try:
        # Removed the "CONNECTING TO QUBIC NETWORK" panel and authentication message
        r = requests.post('https://api.qubic.li/Auth/Login', data=json.dumps(rBody), headers=rHeaders, timeout=10)
        r.raise_for_status()
        token = r.json().get('token')
        
        if token:
            rHeaders = {'Accept': 'application/json', 'Authorization': 'Bearer ' + token}
            
            try:
                r = requests.get('https://api.qubic.li/Score/Get', headers=rHeaders, timeout=10)
                r.raise_for_status()
                networkStat = r.json()
                
                clear_screen()
                
                # Get network statistics
                current_solution_rate = networkStat.get('solutionsPerHourCalculated', 0)  
                current_rate_per_hour = current_solution_rate
                
                scores = networkStat.get('scores', [])
                s = sorted(scores, key=lambda t: t['score'], reverse=True)

                total_ids = len(s)
                computors_count = sum(1 for comp in s if comp.get('isComputor', False))
                candidates_count = sum(1 for comp in s if not comp.get('isComputor', False))

                total_score = sum(comp['adminScore'] for comp in s if 'adminScore' in comp)

                max_score = max(comp['score'] for comp in s) if s else 0
                min_score = min(comp['score'] for comp in s[:676]) if len(s) >= 676 else 0
                
                # Calculate average score with protection against division by zero
                if total_ids > 0:
                    average_score = sum(comp['score'] for comp in s) / total_ids
                else:
                    average_score = 0
                    
                # Calculate theoretical perfect score with protection against division by zero
                theoretical_perfect_score = total_score / 676 if total_score > 0 else 0

                epoch_start, epoch_end = get_epoch_times()
                now = datetime.now(timezone.utc)
                time_elapsed = max(0.001, (now - epoch_start).total_seconds() / 3600)  # Ensure positive non-zero
                time_left_hours = max(0.001, (epoch_end - now).total_seconds() / 3600)  # Ensure positive non-zero
                
                # Safely calculate epoch progress, avoiding division by zero
                total_epoch_time = time_elapsed + time_left_hours
                if total_epoch_time > 0:
                    epoch_progress = time_elapsed / total_epoch_time
                else:
                    epoch_progress = 0  # Default to 0 if calculation is invalid

                projected_avg, _ = calculate_projected_avg(
                    total_score, current_rate_per_hour, epoch_start, epoch_end, final_total_ids=676
                )
                
                logging.info(f"Total Score: {total_score}, Current Solution Rate: {current_rate_per_hour}, Projected Average: {projected_avg}")
                
                # Print the logo
                console.print(Align.center(Text(logo, style="bright_cyan")))
                
                # System time and epoch info with a new color theme
                time_table = Table.grid(expand=True)
                time_table.add_column("Label", style="grey84")
                time_table.add_column("Value", style="green1")
                
                # Convert system time to UTC to match epoch time
                curr_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                epoch_end_str = epoch_end.strftime("%Y-%m-%d %H:%M:%S UTC")
                
                time_table.add_row("SYSTEM TIME:", curr_time)
                time_table.add_row("EPOCH ENDS:", epoch_end_str)
                
                # Add epoch progress with percentage
                if epoch_progress >= 0.75:
                    progress_color = "green1"
                elif epoch_progress >= 0.5:
                    progress_color = "green3"
                elif epoch_progress >= 0.25:
                    progress_color = "yellow1"
                else:
                    progress_color = "orange_red1"
                    
                time_table.add_row(
                    "EPOCH PROGRESS:", 
                    f"[{progress_color}]{epoch_progress:.2%}[/]"
                )
                
                # Create a better progress bar with Unicode blocks
                bar_width = 30
                filled_width = int(epoch_progress * bar_width)
                
                # Build the progress bar
                progress_text = Text()
                progress_text.append("▕", style="dim")
                
                # Fill the completed portion
                if filled_width > 0:
                    progress_text.append("█" * filled_width, style=progress_color)
                
                # Add a transition character
                if 0 < filled_width < bar_width:
                    progress_text.append("▌", style=progress_color)
                    
                # Fill the remaining portion
                if filled_width < bar_width:
                    remaining = bar_width - filled_width - (1 if 0 < filled_width < bar_width else 0)
                    if remaining > 0:
                        progress_text.append("░" * remaining, style="dim")
                
                progress_text.append("▏", style="dim")
                
                # Add progress bar to the table
                time_table.add_row("", progress_text)
                
                console.print(Panel(time_table, style="deep_sky_blue4", border_style="grey50", box=box.ROUNDED))
                
                # Network stats grid - 3 boxes per row with updated colors
                # Row 1
                grid1 = Table.grid(expand=True)
                grid1.add_column("Left")
                grid1.add_column("Middle")
                grid1.add_column("Right")
                
                # First row boxes with new color scheme
                box1 = Panel(
                    Align.center(
                        Text(f"{current_rate_per_hour:.2f}/hour", style="green1"),
                        vertical="middle"
                    ),
                    title="NETWORK SOLUTION RATE",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                )
                
                # Determine color for time left based on hours remaining
                time_left_color = "orange_red1" if time_left_hours <= 12 else "green1"
                
                box2 = Panel(
                    Align.center(
                        Text(f"{time_left_hours:.2f} hours", style=time_left_color),
                        vertical="middle"
                    ),
                    title="TIME LEFT IN EPOCH",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                )
                
                box3 = Panel(
                    Align.center(
                        Text(f"{time_elapsed:.2f} hours", style="green1"),
                        vertical="middle"
                    ),
                    title="TIME ELAPSED",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                )
                
                grid1.add_row(box1, box2, box3)
                console.print(grid1)
                
                # Row 2 with updated color scheme
                grid2 = Table.grid(expand=True)
                grid2.add_column("Left")
                grid2.add_column("Middle")
                grid2.add_column("Right")
                
                # Determine color for projected average progress bar based on comparison to min score
                if projected_avg < min_score * 1.05:  # Less than 5% above min score
                    proj_color = "orange_red1"
                elif projected_avg < min_score * 1.1:  # Less than 10% above min score
                    proj_color = "yellow1"
                else:
                    proj_color = "green1"
                
                # Second row boxes with new colors
                box4 = Panel(
                    Align.center(
                        Text(f"{current_rate_per_hour/676:.4f}/hour", style="green1"),
                        vertical="middle"
                    ),
                    title="SOLUTION RATE (1 ID)",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                )
                
                box5 = Panel(
                    Align.center(
                        Text(f"{theoretical_perfect_score:.2f}", style="green1"),
                        vertical="middle"
                    ),
                    title="PERFECT SCORE (1 ID)",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                )
                
                # Modified: Simplified projected average panel
                proj_content = Table.grid(expand=False)
                proj_content.add_row(f"Projected: [{proj_color}]{projected_avg:.2f}[/]")
                
                progress_panel = Panel(
                    proj_content,
                    title="PROJECTED AVERAGE",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                )
                
                grid2.add_row(box4, box5, progress_panel)
                console.print(grid2)
                
                # Process your active IDs
                your_active_ids = []
                
                # More compact header with less padding and new colors
                header_text = Text("YOUR ACTIVE IDS PERFORMANCE", style="grey84 bold")
                header_panel = Panel(
                    Align.center(header_text),
                    style="dodger_blue1",
                    border_style="dodger_blue1",
                    box=box.SIMPLE,
                    padding=(0, 1)
                )
                console.print(header_panel)
                
                # Create individual containers for each ID
                if any(comp['identity'] in YOUR_IDS and comp['score'] > 0 for comp in s):
                    # List to hold all ID panels
                    id_panels = []
                    
                    for comp in s:
                        if comp['identity'] in YOUR_IDS and comp['score'] > 0:
                            # Extract and calculate values
                            identity = comp['identity']
                            score = comp['score']
                            is_computor = comp.get('isComputor', False)
                            
                            # Calculate rank
                            rank = next((i + 1 for i, x in enumerate(s) if x['identity'] == identity), 0)
                            
                            # Calculate rate
                            if time_elapsed > 0:
                                rate = score / time_elapsed 
                            else:
                                rate = 0
                            
                            # Determine status colors and text based on rank - updated colors
                            if rank > 450:
                                status_color = "orange_red1"
                                status_text = "DANGER"
                            elif rank > 250:
                                status_color = "gold1"
                                status_text = "CAUTION"
                            else:
                                status_color = "green1"
                                status_text = "OPTIMAL"
                            
                            # Calculate score as percentage of projected average
                            score_vs_projected = (score / projected_avg) if projected_avg > 0 else 0
                            
                            # Format numbers as requested
                            score_formatted = f"{int(score)}"  # No decimal
                            rate_formatted = f"{rate:.2f}"     # 2 decimal places
                            
                            # Create an aesthetic progress bar
                            progress_percentage = min(score_vs_projected, 1.0)
                            bar_width = 30  # Increased for better visibility
                            filled_width = int(progress_percentage * bar_width)
                            
                            # Color logic according to requirements - updated colors
                            if progress_percentage >= 0.9:
                                bar_color = "green1"
                            elif progress_percentage >= 0.5:
                                bar_color = "gold1"
                            else:
                                bar_color = "orange_red1"
                            
                            # Build the progress bar with Unicode block characters
                            progress_bar = Text()
                            progress_bar.append("▕", style="dim")
                            
                            # Fill the completed portion
                            if filled_width > 0:
                                progress_bar.append("█" * filled_width, style=bar_color)
                            
                            # Add a transition character at the end of the filled portion
                            if 0 < filled_width < bar_width:
                                progress_bar.append("▌", style=bar_color)
                                
                            # Fill the remaining portion
                            if filled_width < bar_width:
                                remaining = bar_width - filled_width - (1 if 0 < filled_width < bar_width else 0)
                                if remaining > 0:
                                    progress_bar.append("░" * remaining, style="dim")
                            
                            progress_bar.append("▏", style="dim")
                            
                            # Create content for the ID panel
                            content = Table.grid(expand=True)
                            content.add_column("Col1", justify="left", ratio=1, no_wrap=True)
                            content.add_column("Col2", justify="right", ratio=1, no_wrap=True)
                            
                            # Row 1: ID - display full identity with updated color
                            content.add_row(
                                Text(identity, style="deep_sky_blue1", overflow="fold"),
                                ""
                            )
                            
                            # Row 2: Rank with status and Score with Rate
                            content.add_row(
                                Text.assemble(
                                    Text("RANK: ", style="white"),
                                    Text(f"#{rank}", style=f"bold {status_color}"),
                                    Text(" "),
                                    Text(f"[{status_text}]", style=f"bold {status_color}")
                                ),
                                Text.assemble(
                                    Text("SCORE: ", style="white"),
                                    Text(score_formatted, style=f"bold {status_color}"),
                                    Text(" | RATE: ", style="white"),
                                    Text(f"{rate_formatted}/h", style=f"bold {status_color}")
                                )
                            )
                            
                            # Row 3: Progress with percentage and bar
                            content.add_row(
                                Text.assemble(
                                    Text("PROGRESS: ", style="white"),
                                    Text(f"{score_vs_projected:.1%}", style=f"bold {bar_color}")
                                ),
                                ""
                            )
                            
                            # Row 4: Progress bar
                            content.add_row(progress_bar, "")
                            
                            # Create the panel title
                            computor_icon = "✓" if is_computor else "✗"
                            panel_title = f"[{status_color}]{computor_icon} {'COMPUTOR' if is_computor else 'CANDIDATE'}[/]"
                            
                            # Create the ID panel
                            panel = Panel(
                                content,
                                title=panel_title,
                                border_style=status_color,
                                box=box.ROUNDED,
                                padding=(0, 1)
                            )
                            
                            id_panels.append(panel)
                            
                            # Add to active IDs for summary calculations
                            your_active_ids.append((identity, rank, score, rate))
                    
                    # Display all ID panels in a vertical list for space efficiency
                    for panel in id_panels:
                        console.print(panel)
                        
                else:
                    console.print(
                        Panel(
                            Align.center("[yellow]No active IDs found with positive scores[/]"),
                            style="yellow",
                            border_style="bright_yellow",
                            box=box.ROUNDED
                        )
                    )
                
                # Summary section for your IDs with updated colors
                if your_active_ids:
                    active_ranks = [rank for _, rank, _, _ in your_active_ids]
                    total_your_score = sum(score for _, _, score, _ in your_active_ids)
                    
                    # Protect against division by zero for average score calculation
                    if len(your_active_ids) > 0:
                        avg_your_score = total_your_score / len(your_active_ids)
                    else:
                        avg_your_score = 0
                        
                    your_total_rate = sum(rate for _, _, _, rate in your_active_ids)
                    
                    # Calculate new ID potential first to have score_vs_perfect defined
                    whole_ids, partial_progress, solutions_needed, time_to_next, score_vs_perfect, theoretical_perfect_score = calculate_new_id_potential(
                        total_your_score, 
                        your_total_rate,
                        total_score
                    )
                    console.print("")
                    console.print(Panel(
                        "[grey84]YOUR IDS SUMMARY",
                        style="dodger_blue1", 
                        box=box.HEAVY
                    ))
                    
                    # Create a more visually appealing summary with updated colors
                    summary_panels = []
                    
                    # IDs count panel
                    id_count_panel = Panel(
                        Align.center(Text(f"{len(your_active_ids)}", style="green1", justify="center"), vertical="middle"),
                        title="ACTIVE IDS",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    summary_panels.append(id_count_panel)
                    
                    # Rank panel with updated colors
                    rank_info = Table.grid(expand=True)
                    rank_info.add_column("Info", style="grey84")
                    rank_info.add_column("Value")
                    
                    # Determine color based on rank values
                    best_rank = min(active_ranks)
                    worst_rank = max(active_ranks)
                    avg_rank = sum(active_ranks) / len(active_ranks)
                    
                    best_color = "orange_red1" if best_rank > 450 else "green1"
                    worst_color = "orange_red1" if worst_rank > 450 else "green1"
                    avg_color = "orange_red1" if avg_rank > 450 else "green1"
                    
                    rank_info.add_row("BEST:", f"[{best_color}]#{best_rank}[/]")
                    rank_info.add_row("WORST:", f"[{worst_color}]#{worst_rank}[/]")
                    rank_info.add_row("AVERAGE:", f"[{avg_color}]#{avg_rank:.0f}[/]")
                    
                    rank_panel = Panel(
                        rank_info,
                        title="RANKS",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    summary_panels.append(rank_panel)
                    
                    # Score panel with updated colors
                    score_info = Table.grid(expand=True)
                    score_info.add_column("Info", style="grey84")
                    score_info.add_column("Value", style="green1")
                    
                    score_info.add_row("TOTAL:", f"{int(total_your_score)}")
                    score_info.add_row("AVERAGE:", f"{avg_your_score:.2f}")
                    score_info.add_row("SOLUTION RATE:", f"{your_total_rate:.2f}/h")
                    
                    score_panel = Panel(
                        score_info,
                        title="SCORES",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    summary_panels.append(score_panel)
                    
                    # Display the summary panels in a grid
                    summary_grid = Table.grid(expand=True)
                    summary_grid.add_column("Left", justify="center", ratio=1)
                    summary_grid.add_column("Middle", justify="center", ratio=1)
                    summary_grid.add_column("Right", justify="center", ratio=1)
                    
                    summary_grid.add_row(*summary_panels)
                    console.print(summary_grid)
                    
                    # New ID potential analysis with improved colors
                    console.print("")
                    console.print(Panel(
                        "[grey84]NEW ID POTENTIAL ANALYSIS",
                        style="dodger_blue1", 
                        box=box.HEAVY
                    ))
                    
                    # Create beautiful panels for potential analysis with updated colors
                    potential_panels = []
                    
                    # Score ratio panel
                    ratio_info = Table.grid(expand=True)
                    ratio_info.add_column("Metric", style="grey84")
                    ratio_info.add_column("Value", style="green1")
                    
                    ratio_info.add_row("TOTAL SCORE VS NET. AVG:", f"{total_your_score / average_score:.2f}")
                    ratio_info.add_row("TOTAL SCORE VS 676 COMPS.", f"{score_vs_perfect:.2f}")
                    
                    ratio_panel = Panel(
                        ratio_info,
                        title="SCORE RATIOS",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    potential_panels.append(ratio_panel)
                    
                    # ID completion progress color with enhanced appearance
                    id_progress_color = "green1" if partial_progress > 0.75 else "gold1" if partial_progress > 0.5 else "deep_sky_blue1" if partial_progress > 0.25 else "orange_red1"
                    
                    completion_info = Table.grid(expand=True)
                    completion_info.add_column("Info", style="grey84")
                    completion_info.add_column("Value")
                    
                    completion_info.add_row("COMPLETE IDS:", f"[green1]{whole_ids}[/]")
                    completion_info.add_row("PROGRESS TO NEXT:", f"[{id_progress_color}]{partial_progress:.1%}[/]")
                    # Progress bar removed
                    
                    completion_panel = Panel(
                        completion_info,
                        title="ID COMPLETION",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    potential_panels.append(completion_panel)
                    
                    # Solutions panel with updated colors
                    next_time_str = "N/A (No solutions yet)" if time_to_next == float('inf') else f"{time_to_next:.2f} hours"
                    
                    solution_info = Table.grid(expand=True)
                    solution_info.add_column("Info", style="grey84")
                    solution_info.add_column("Value", style="green1")
                    
                    solution_info.add_row("NEEDED:", f"{solutions_needed:.2f}")
                    solution_info.add_row("TIME TO NEXT ID:", next_time_str)
                    
                    solution_panel = Panel(
                        solution_info,
                        title="SOLUTIONS",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    potential_panels.append(solution_panel)
                    
                    # Display the potential panels in a grid
                    potential_grid = Table.grid(expand=True)
                    potential_grid.add_column("Left", justify="center", ratio=1)
                    potential_grid.add_column("Middle", justify="center", ratio=1)
                    potential_grid.add_column("Right", justify="center", ratio=1)
                    
                    potential_grid.add_row(*potential_panels)
                    console.print(potential_grid)
                    
                    # Removed the ID STRATEGY RECOMMENDATIONS section
                
                # Network statistics with improved colors
                console.print("")
                console.print(Panel(
                    "[grey84]NETWORK STATISTICS",
                    style="dodger_blue1", 
                    box=box.HEAVY
                ))
                
                # Create network stat panels with updated colors
                net_stat_panels_row1 = []
                
                # IDs count panel
                id_counts = Table.grid(expand=True)
                id_counts.add_column("Type", style="grey84")
                id_counts.add_column("Count", style="green1")
                
                id_counts.add_row("TOTAL:", f"{total_ids}")
                id_counts.add_row("COMPUTORS:", f"{computors_count}")
                id_counts.add_row("CANDIDATES:", f"{candidates_count}")
                
                id_count_panel = Panel(
                    id_counts,
                    title="ID COUNTS",
                    border_style="deep_sky_blue1",
                    box=box.ROUNDED
                )
                net_stat_panels_row1.append(id_count_panel)
                
                # Score metrics panel with updated colors
                score_metrics = Table.grid(expand=True)
                score_metrics.add_column("Metric", style="grey84")
                score_metrics.add_column("Value", style="green1")
                
                score_metrics.add_row("MAX:", f"{int(max_score)}")
                score_metrics.add_row("MIN (TOP 676):", f"{int(min_score)}")
                score_metrics.add_row("AVERAGE:", f"{average_score:.2f}")
                
                score_panel = Panel(
                    score_metrics,
                    title="SCORE METRICS",
                    border_style="deep_sky_blue1",
                    box=box.ROUNDED
                )
                net_stat_panels_row1.append(score_panel)
                
                # Other metrics panel with updated colors
                other_metrics = Table.grid(expand=True)
                other_metrics.add_column("Metric", style="grey84")
                other_metrics.add_column("Value", style="green1")
                
                other_metrics.add_row("PERFECT/ID:", f"{theoretical_perfect_score:.2f}")
                other_metrics.add_row("PROJECTED AVG:", f"{projected_avg:.2f}")
                other_metrics.add_row("TOTAL SCORE:", f"{int(total_score)}")
                
                other_panel = Panel(
                    other_metrics,
                    title="OTHER METRICS",
                    border_style="deep_sky_blue1",
                    box=box.ROUNDED
                )
                net_stat_panels_row1.append(other_panel)
                
                # Display the network stat panels in a grid
                net_stat_grid = Table.grid(expand=True)
                net_stat_grid.add_column("Left", justify="center", ratio=1)
                net_stat_grid.add_column("Middle", justify="center", ratio=1)
                net_stat_grid.add_column("Right", justify="center", ratio=1)
                
                net_stat_grid.add_row(*net_stat_panels_row1)
                console.print(net_stat_grid)
                
                # Add your total solution rate if available
                if your_active_ids:
                    solution_rate_panel = Panel(
                        Align.center(
                            Text(f"{your_total_rate:.4f}/hour", style="bright_green"),
                            vertical="middle"
                        ),
                        title="YOUR TOTAL SOLUTION RATE",
                        border_style="green",
                        box=box.ROUNDED
                    )
                    # Modified solution rate to 2 decimal places in the panel with updated colors
                    solution_rate_panel = Panel(
                        Align.center(
                            Text(f"{your_total_rate:.2f}/hour", style="green1"),
                            vertical="middle"
                        ),
                        title="YOUR TOTAL SOLUTION RATE",
                        border_style="deep_sky_blue1",
                        box=box.ROUNDED
                    )
                    console.print(solution_rate_panel)
                
                # Footer with updated colors
                console.print("")
                console.print(Panel(
                    f"[gold1]NEXT UPDATE IN 5 MINUTES[/] | [green3]{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}[/]",
                    style="deep_sky_blue4",
                    border_style="steel_blue1",
                    box=box.ROUNDED
                ))

            except requests.exceptions.Timeout as errt:
                logging.error(f"Timeout error during score fetching: {errt}")
                console.print(Panel(f"[bold red]CONNECTION TIMEOUT: {errt}[/]", style="red"))

        else:
            logging.error("Authentication failed. No token received.")
            console.print(Panel("[bold red]AUTHENTICATION FAILED: No token received[/]", style="red"))

    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout error during authentication: {errt}")
        console.print(Panel(f"[bold red]CONNECTION TIMEOUT: {errt}[/]", style="red"))
    except requests.exceptions.RequestException as err:
        logging.error(f"API error: {err}")
        console.print(Panel(f"[bold red]API ERROR: {err}[/]", style="red"))
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        console.print(Panel(f"[bold red]SYSTEM ERROR: {e}[/]", style="red"))

def main():
    while True:
        try:
            fetch_scores()
            time.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            clear_screen()
            console.print("[bold red]⚠ SYSTEM TERMINATED BY USER ⚠[/]")
            logging.info("Process interrupted by user.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            console.print(f"[bold red]Critical error: {e}[/]")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()
