#!/usr/bin/env python3

import subprocess
import time
from typing import List, Dict, Tuple
import logging
from datetime import datetime
import threading
from queue import Queue
import psutil
import os
import json
import random
import requests  # For API calls to get latest tick
import re  # For regex to extract hash from output
import pandas as pd  # For Excel file handling (optional)

# Configuration
NODES = [
    "NODE1",
    "NODE2",
    "NODE3"
]

QUBIC_CLI_PATH = "qubic-cli.exe"

# Hardcoded wallet information
DEFAULT_SEED = "SEED"
DEFAULT_ADDRESS = "WLT"

# Tick advance - schedule transactions this many ticks ahead of current
TICK_ADVANCE = 20

# API endpoint for checking latest network tick
QUBIC_API_ENDPOINT = "https://rpc.qubic.org/v1/latestTick"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qus_sender.log'),
        logging.StreamHandler()
    ]
)

def get_latest_network_tick():
    """Query the Qubic API to get the latest confirmed tick"""
    try:
        response = requests.get(QUBIC_API_ENDPOINT, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("latestTick")
        else:
            logging.error(f"API request failed with status code {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error querying latest tick: {str(e)}")
        return None

def wait_for_tick_confirmation(target_tick, check_interval=5):
    """Wait until the network has processed past the target tick"""
    while True:
        latest_tick = get_latest_network_tick()
        if latest_tick is None:
            logging.warning("Failed to get latest tick, retrying in 5 seconds")
            time.sleep(5)
            continue
            
        if latest_tick >= target_tick:
            logging.info(f"Tick {target_tick} has been confirmed by the network (latest: {latest_tick})")
            return True
            
        logging.info(f"Waiting for tick {target_tick} confirmation. Current network tick: {latest_tick}. Checking again in {check_interval} seconds")
        time.sleep(check_interval)

def parse_pasted_data(data_text):
    """Parse pasted data with columns Amount and WLT ADDRESS"""
    try:
        lines = data_text.strip().split('\n')
        payment_data = []
        
        # Skip the header if it exists (first line with "Amount" and "WLT ADDRESS")
        start_idx = 0
        if "amount" in lines[0].lower() and "address" in lines[0].lower():
            start_idx = 1
        
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
                
            # Find where the numeric amount ends and the wallet address begins
            # Wallet addresses in Qubic are alphanumeric and typically uppercase
            amount_end = 0
            for j, char in enumerate(line):
                if char.isalpha():
                    amount_end = j
                    break
            
            if amount_end > 0:
                try:
                    amount_str = line[:amount_end].strip()
                    wallet_address = line[amount_end:].strip()
                    
                    # Validate data
                    if not amount_str.isdigit():
                        logging.warning(f"Invalid amount in line {i+1}: {amount_str}")
                        continue
                        
                    if len(wallet_address) < 10:  # Arbitrary minimum length for a valid wallet address
                        logging.warning(f"Invalid wallet address in line {i+1}: {wallet_address}")
                        continue
                    
                    payment_data.append({
                        'wallet_address': wallet_address,
                        'amount': int(amount_str),
                        'sols': None  # No sols info in this format
                    })
                except Exception as e:
                    logging.warning(f"Error parsing line {i+1}: {str(e)}")
            else:
                logging.warning(f"Could not parse line {i+1}: {line}")
        
        logging.info(f"Parsed {len(payment_data)} payment records from pasted data")
        return payment_data
    except Exception as e:
        logging.error(f"Error parsing pasted data: {str(e)}")
        raise

def load_excel_data(excel_file):
    """Load payment data from Excel file"""
    try:
        df = pd.read_excel(excel_file)
        payment_data = []
        
        # Assuming columns are: 'wallet_address', 'amount', and optionally 'sols'
        for idx, row in df.iterrows():
            payment_data.append({
                'wallet_address': str(row['wallet_address']).strip(),
                'amount': int(row['amount']),
                'sols': str(row.get('sols', '')) if 'sols' in df.columns else None
            })
        
        logging.info(f"Loaded {len(payment_data)} payment records from Excel file")
        return payment_data
    except Exception as e:
        logging.error(f"Error loading Excel file: {str(e)}")
        raise

class QUSSender:
    def __init__(self, source_wallet, payment_data):
        self.active_nodes = NODES.copy()
        self.current_node_index = 0
        self.active_processes = set()
        
        # Source wallet information
        self.source_wallet = source_wallet
        
        # Payment data (addresses and amounts)
        self.payment_data = payment_data
        
        # Transaction tracking
        self.current_tx_hash = None
        self.current_tx_target = None
        self.current_tx_tick = None
        self.current_tx_amount = None
        
        # Failed transactions
        self.failed_transactions = []
        
        # File to save failed transactions
        self.failed_tx_file = "failed_transactions.json"

    def get_next_node(self) -> str:
        """Get current node and switch to next if current is unavailable"""
        if not self.active_nodes:
            raise Exception("No active nodes available")
        
        # Ensure index is within bounds
        if self.current_node_index >= len(self.active_nodes):
            self.current_node_index = 0
        
        return self.active_nodes[self.current_node_index]

    def switch_to_next_node(self):
        """Switch to the next available node"""
        if not self.active_nodes:
            raise Exception("No active nodes available")
        
        # Move to next node in circular logic
        self.current_node_index = (self.current_node_index + 1) % len(self.active_nodes)
        logging.info(f"Switched to node: {self.active_nodes[self.current_node_index]}")

    def extract_tx_hash(self, output_text):
        """Extract transaction hash from the transaction output"""
        try:
            match = re.search(r'TxHash: ([a-zA-Z0-9]+)', output_text)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            logging.error(f"Error extracting transaction hash: {str(e)}")
            return None

    def send_transaction(self, target_address, amount, tick, retry_count=0, max_retries=3):
        """Send a transaction with the specified amount to the target address for the given tick"""
        process = None
        try:
            node = self.get_next_node()
            cmd = [
                QUBIC_CLI_PATH,
                '-nodeip', node,
                '-seed', self.source_wallet['seed'],
                '-sendtoaddressintick', target_address,
                str(amount),
                str(tick)
            ]
            
            logging.info(f"Attempting transaction with node: {node}")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.active_processes.add(process.pid)
            
            stdout, stderr = process.communicate(timeout=30)  # 30 second timeout
            stdout_text = stdout.decode()
            stderr_text = stderr.decode()
            
            # Print the full output for inspection
            print(stdout_text)
            
            # Check for specific success message
            if "Transaction has been sent!" in stdout_text:
                # Extract transaction hash
                tx_hash = self.extract_tx_hash(stdout_text)
                if tx_hash:
                    logging.info(f"Transaction successful: {self.source_wallet['address']} -> {target_address} for {amount} QUS, tick {tick}, hash: {tx_hash}")
                    return True, tx_hash
                else:
                    logging.warning(f"Transaction sent but couldn't extract hash: {self.source_wallet['address']} -> {target_address}")
                    return True, None
            
            # Handle connection failures
            if "Failed to connect" in stderr_text or "error -1" in stderr_text:
                logging.warning(f"Node {node} connection failed")
                
                # Switch to next node for retry
                self.switch_to_next_node()
                
                # Retry with new node if we haven't exceeded max retries
                if retry_count < max_retries:
                    logging.info(f"Retrying transaction to {target_address} with next node (Attempt {retry_count + 2}/{max_retries + 1})")
                    return self.send_transaction(target_address, amount, tick, retry_count + 1, max_retries)
                
                logging.error(f"Max retries ({max_retries}) reached for transaction to {target_address}")
                return False, None
            
            # Any other failure
            logging.error(f"Transaction failed: {stderr_text}")
            if retry_count < max_retries:
                # Try next node on any failure
                self.switch_to_next_node()
                logging.info(f"Retrying transaction to {target_address} (Attempt {retry_count + 2}/{max_retries + 1})")
                return self.send_transaction(target_address, amount, tick, retry_count + 1, max_retries)
            
            return False, None
            
        except subprocess.TimeoutExpired:
            logging.error(f"Transaction timed out on node {self.active_nodes[self.current_node_index]}")
            if process:
                process.kill()
            
            # Switch to next node on timeout
            self.switch_to_next_node()
            
            if retry_count < max_retries:
                logging.info(f"Retrying transaction to {target_address} (Attempt {retry_count + 2}/{max_retries + 1})")
                return self.send_transaction(target_address, amount, tick, retry_count + 1, max_retries)
            
            return False, None
        except Exception as e:
            logging.error(f"Error processing transaction: {str(e)}")
            
            # Switch to next node on exception
            self.switch_to_next_node()
            
            if retry_count < max_retries:
                logging.info(f"Retrying transaction to {target_address} (Attempt {retry_count + 2}/{max_retries + 1})")
                return self.send_transaction(target_address, amount, tick, retry_count + 1, max_retries)
            
            return False, None
        finally:
            if process and process.pid in self.active_processes:
                self.active_processes.remove(process.pid)

    def verify_transaction(self, retry_count=0, max_retries=3):
        """Verify if the current transaction was accepted on the network"""
        if not self.current_tx_hash or not self.current_tx_tick:
            logging.warning("No current transaction to verify")
            return False
            
        try:
            node = self.get_next_node()
            cmd = [
                QUBIC_CLI_PATH,
                '-nodeip', node,
                '-checktxontick', str(self.current_tx_tick),
                self.current_tx_hash
            ]
            
            logging.info(f"Verifying transaction with node: {node}")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=30)
            stdout_text = stdout.decode()
            stderr_text = stderr.decode()
            
            # Print the full verification output
            print(stdout_text)
            
            # Check if tick hasn't passed yet
            if "Please wait a bit more" in stdout_text:
                logging.info(f"Tick {self.current_tx_tick} not processed yet. Will check again later.")
                return None  # Not yet confirmed
                
            # Check if transaction not found
            if "Can NOT find tx" in stdout_text:
                logging.warning(f"Transaction {self.current_tx_hash} not found on tick {self.current_tx_tick}")
                return False  # Transaction was rejected
                
            # Check if transaction was accepted
            if "Found tx" in stdout_text and "Received end response message" in stdout_text:
                logging.info(f"Transaction {self.current_tx_hash} confirmed on tick {self.current_tx_tick}")
                return True  # Transaction was accepted
            
            # Handle connection failures during verification
            if "Failed to connect" in stderr_text or "error -1" in stderr_text:
                logging.warning(f"Node connection failed during verification")
                self.switch_to_next_node()
                
                if retry_count < max_retries:
                    logging.info(f"Retrying verification for {self.current_tx_hash} (Attempt {retry_count + 2}/{max_retries + 1})")
                    return self.verify_transaction(retry_count + 1, max_retries)
            
            # Handle other responses
            logging.warning(f"Unexpected response for tx verification: {stdout_text}")
            if retry_count < max_retries:
                self.switch_to_next_node()
                logging.info(f"Retrying verification for {self.current_tx_hash} (Attempt {retry_count + 2}/{max_retries + 1})")
                return self.verify_transaction(retry_count + 1, max_retries)
                
            return False  # Consider as failed after max retries
            
        except Exception as e:
            logging.error(f"Error verifying transaction: {str(e)}")
            self.switch_to_next_node()
            
            if retry_count < max_retries:
                logging.info(f"Retrying verification for {self.current_tx_hash} (Attempt {retry_count + 2}/{max_retries + 1})")
                return self.verify_transaction(retry_count + 1, max_retries)
                
            return False  # Consider as failed after max retries

    def verify_specific_transaction(self, tx_hash, tick, retry_count=0, max_retries=3):
        """Verify a specific transaction by hash and tick"""
        if not tx_hash or not tick:
            logging.warning("Invalid transaction hash or tick for verification")
            return False
            
        try:
            node = self.get_next_node()
            cmd = [
                QUBIC_CLI_PATH,
                '-nodeip', node,
                '-checktxontick', str(tick),
                tx_hash
            ]
            
            logging.info(f"Verifying transaction {tx_hash} on tick {tick} with node: {node}")
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=30)
            stdout_text = stdout.decode()
            stderr_text = stderr.decode()
            
            # Check if transaction was accepted
            if "Found tx" in stdout_text and "Received end response message" in stdout_text:
                logging.info(f"Transaction {tx_hash} confirmed on tick {tick}")
                return True
                
            # Check if transaction not found
            if "Can NOT find tx" in stdout_text:
                logging.info(f"Transaction {tx_hash} not found on tick {tick}")
                return False
            
            # Handle connection failures during verification
            if "Failed to connect" in stderr_text or "error -1" in stderr_text:
                logging.warning(f"Node connection failed during verification")
                self.switch_to_next_node()
                
                if retry_count < max_retries:
                    return self.verify_specific_transaction(tx_hash, tick, retry_count + 1, max_retries)
            
            # Handle other responses
            if retry_count < max_retries:
                self.switch_to_next_node()
                return self.verify_specific_transaction(tx_hash, tick, retry_count + 1, max_retries)
                
            return False
            
        except Exception as e:
            logging.error(f"Error verifying transaction {tx_hash}: {str(e)}")
            self.switch_to_next_node()
            
            if retry_count < max_retries:
                return self.verify_specific_transaction(tx_hash, tick, retry_count + 1, max_retries)
                
            return False

    def reverify_failed_transactions(self, successful_transactions):
        """Reverify all failed transactions to catch any that actually succeeded"""
        if not self.failed_transactions:
            return
        
        print("\n" + "="*60)
        print("FINAL REVERIFICATION OF FAILED TRANSACTIONS")
        print("="*60)
        print(f"Reverifying {len(self.failed_transactions)} failed transactions...")
        print("This may take a few moments...\n")
        
        actually_successful = []
        still_failed = []
        
        for idx, failed_tx in enumerate(self.failed_transactions):
            tx_hash = failed_tx.get('tx_hash')
            tick = failed_tx.get('tick')
            wallet_address = failed_tx['wallet_address']
            amount = failed_tx['amount']
            
            print(f"Reverifying {idx+1}/{len(self.failed_transactions)}: {wallet_address[:20]}...")
            
            # Skip transactions without hash (they never made it to the network)
            if not tx_hash:
                print(f"  ✗ No transaction hash - transaction never sent")
                still_failed.append(failed_tx)
                continue
            
            # Verify the transaction
            is_confirmed = self.verify_specific_transaction(tx_hash, tick)
            
            if is_confirmed:
                print(f"  ✓ Transaction actually succeeded!")
                logging.info(f"Reverification: Transaction {tx_hash} to {wallet_address} was actually successful")
                actually_successful.append(failed_tx)
            else:
                print(f"  ✗ Transaction still failed")
                still_failed.append(failed_tx)
            
            time.sleep(1)  # Brief pause between verifications
        
        # Update the lists
        if actually_successful:
            print(f"\n{len(actually_successful)} transaction(s) were actually successful!")
            # Add to successful transactions list
            successful_transactions.extend(actually_successful)
            
        # Update failed transactions list to only include truly failed ones
        self.failed_transactions = still_failed
        
        print(f"After reverification: {len(successful_transactions)} successful, {len(still_failed)} failed\n")

    def save_failed_transactions(self):
        """Save failed transaction data to a file"""
        try:
            with open(self.failed_tx_file, 'w') as f:
                json.dump(self.failed_transactions, f, indent=4)
            logging.info(f"Saved {len(self.failed_transactions)} failed transactions to {self.failed_tx_file}")
        except Exception as e:
            logging.error(f"Error saving failed transactions: {str(e)}")

    def create_transaction_report(self, successful_transactions):
        """Create a detailed report of all successful transactions"""
        report_file = "transaction_report.txt"
        try:
            with open(report_file, 'w') as f:
                f.write("QUBIC TRANSACTION REPORT\n")
                f.write("=======================\n\n")
                f.write(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source wallet: {self.source_wallet['address']}\n\n")
                f.write("TRANSACTION DETAILS:\n")
                f.write("-----------------\n\n")
                
                for idx, tx in enumerate(successful_transactions):
                    f.write(f"Transaction #{idx+1}:\n")
                    f.write(f"  Recipient Address: {tx['wallet_address']}\n")
                    f.write(f"  Amount: {tx['amount']} QUS\n")
                    if tx.get('sols'):
                        f.write(f"  Sols Info: {tx['sols']}\n")
                    f.write(f"  Tick: {tx['tick']}\n")
                    f.write(f"  Transaction Hash: {tx['tx_hash']}\n")
                    f.write(f"  Transaction Link: https://explorer.qubic.org/network/tx/{tx['tx_hash']}\n\n")
                
                f.write(f"\nTotal successful transactions: {len(successful_transactions)}\n")
                if self.failed_transactions:
                    f.write(f"Failed transactions: {len(self.failed_transactions)} (see failed_transactions.json for details)\n")
            
            print(f"\nTransaction report created: {report_file}")
            return True
        except Exception as e:
            logging.error(f"Error creating transaction report: {str(e)}")
            return False

    def run(self):
        """Run the sender processing one transaction at a time"""
        try:
            print("\nQubic Excel-based QUS Sender - Sequential Mode")
            print("=============================================")
            
            # Display all transactions for review before starting
            print("\nREVIEW ALL PLANNED TRANSACTIONS:")
            print("--------------------------------")
            total_amount = 0
            print(f"{'#':<5} {'Wallet Address':<50} {'Amount (QUS)':<15} {'Sols Info':<20}")
            print("-" * 90)
            for idx, payment in enumerate(self.payment_data):
                address = payment['wallet_address']
                amount = payment['amount']
                sols = payment['sols'] if payment['sols'] else "N/A"
                print(f"{idx+1:<5} {address:<50} {amount:<15} {sols:<20}")
                total_amount += amount
            
            print("-" * 90)
            print(f"Total transactions: {len(self.payment_data)}")
            print(f"Total QUS to be sent: {total_amount}")
            
            # Confirm before proceeding
            proceed = input("\nPlease review the above transactions. Proceed with sending? (y/n): ")
            if proceed.lower() != 'y':
                print("Operation cancelled by user")
                return
            
            print(f"\nProcessing transactions one at a time, waiting for each tick to complete")
            print(f"Available nodes: {', '.join(self.active_nodes)}")
            print(f"Starting with node: {self.active_nodes[self.current_node_index]}\n")
            
            # List to track successful transactions
            successful_transactions = []
            
            # Process transactions one by one
            for idx, payment in enumerate(self.payment_data):
                # Get current network tick for scheduling
                current_network_tick = get_latest_network_tick()
                if current_network_tick is None:
                    logging.warning("Failed to get current network tick, retrying in 5 seconds")
                    time.sleep(5)
                    continue
                
                # Calculate target tick (current + TICK_ADVANCE)
                target_tick = current_network_tick + TICK_ADVANCE
                
                # Get payment details
                target_address = payment['wallet_address']
                amount = payment['amount']
                sols_info = payment['sols']
                
                print(f"\nTransaction {idx+1}/{len(self.payment_data)}")
                print(f"--------------------------------------------------")
                print(f"Target Address: {target_address}")
                print(f"Amount: {amount} QUS")
                if sols_info:
                    print(f"Sols Info: {sols_info}")
                print(f"Current Network Tick: {current_network_tick}")
                print(f"Target Tick: {target_tick} ({TICK_ADVANCE} ticks ahead)")
                
                # Send transaction
                print(f"Sending transaction...")
                success, tx_hash = self.send_transaction(target_address, amount, target_tick)
                
                if success and tx_hash:
                    # Store current transaction info for verification
                    self.current_tx_hash = tx_hash
                    self.current_tx_target = target_address
                    self.current_tx_tick = target_tick
                    self.current_tx_amount = amount
                    
                    # Wait for tick to be confirmed
                    print(f"Waiting for tick {target_tick} to be confirmed by the network...")
                    wait_for_tick_confirmation(target_tick)
                    
                    # Verify transaction
                    print(f"Verifying transaction {tx_hash}...")
                    verification_result = self.verify_transaction()
                    
                    # If transaction is still pending, keep checking
                    while verification_result is None:
                        print(f"Transaction still pending. Checking again in 5 seconds...")
                        time.sleep(5)
                        verification_result = self.verify_transaction()
                    
                    if verification_result:
                        print(f"Transaction verified successfully!")
                        # Add to successful transactions list
                        successful_transactions.append({
                            'wallet_address': target_address,
                            'amount': amount,
                            'sols': sols_info,
                            'tx_hash': tx_hash,
                            'tick': target_tick
                        })
                    else:
                        print(f"Transaction verification failed!")
                        self.failed_transactions.append({
                            'wallet_address': target_address,
                            'amount': amount,
                            'sols': sols_info,
                            'tx_hash': tx_hash,
                            'tick': target_tick
                        })
                else:
                    print(f"Failed to send transaction to {target_address}")
                    self.failed_transactions.append({
                        'wallet_address': target_address,
                        'amount': amount,
                        'sols': sols_info,
                        'tx_hash': None,
                        'tick': target_tick
                    })
                
                # Brief pause between transactions
                time.sleep(2)
            
            # Before finalizing results, reverify all failed transactions
            if self.failed_transactions:
                self.reverify_failed_transactions(successful_transactions)
            
            # Create transaction report
            if successful_transactions:
                print(f"\nCreating transaction report for {len(successful_transactions)} successful transactions...")
                self.create_transaction_report(successful_transactions)
            
            # After all transactions and reverification, check if we have any failed ones
            if self.failed_transactions:
                print(f"\nCompleted with {len(successful_transactions)} successful and {len(self.failed_transactions)} failed transactions")
                print("\nFailed transactions:")
                for failed in self.failed_transactions:
                    print(f"  Address: {failed['wallet_address']}, Amount: {failed['amount']} QUS")
                
                self.save_failed_transactions()
                
                # Ask if user wants to retry failed transactions
                retry = input("\nDo you want to retry these failed transactions? (y/n): ").lower() == 'y'
                
                if retry:
                    # Copy failed transactions and clear the list
                    retry_payments = self.failed_transactions.copy()
                    self.failed_transactions = []
                    
                    # Update payment data to retry only failed ones
                    self.payment_data = retry_payments
                    
                    # Recurse to retry
                    print("\nRetrying failed transactions...")
                    self.run()
            else:
                print("\nAll transactions completed successfully!")
        
        except KeyboardInterrupt:
            print("\nOperation interrupted by user")
            logging.info("Shutting down...")
        except Exception as e:
            logging.error(f"Error in operation: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        print("Qubic QUS Sender Tool")
        print("====================")
        
        # Ask if user wants to use default wallet or provide their own
        use_default = input("Use default wallet from code? (y/n): ").lower() == 'y'
        
        if use_default:
            source_wallet = {
                'seed': DEFAULT_SEED,
                'address': DEFAULT_ADDRESS
            }
            print(f"Using default wallet: {DEFAULT_ADDRESS}")
        else:
            # Load source wallet
            wallet_file = input("Enter the path to your source wallet file (containing seed and address): ")
            with open(wallet_file, 'r') as f:
                lines = f.read().strip().split('\n')
                source_wallet = {
                    'seed': lines[0].strip(),
                    'address': lines[1].strip()
                }
            print(f"Loaded source wallet: {source_wallet['address']}")
        
        # Ask user for input method
        input_method = input("Choose input method:\n1. Paste data directly\n2. Load from Excel file\nEnter choice (1 or 2): ")
        
        if input_method == "1":
            print("\nPaste your data below (format: Amount followed by WLT ADDRESS).")
            print("For example:\n36850869NESBZWPNYFGLECLJQVIETDICMYUCMXJKCIHCTRVPLAUEQPUAJMMLHZXFXIQJ")
            print("Press Enter twice when done pasting:\n")
            
            # Collect multi-line input until empty line
            lines = []
            while True:
                line = input()
                if line:
                    lines.append(line)
                else:
                    break
                    
            pasted_data = "\n".join(lines)
            payment_data = parse_pasted_data(pasted_data)
            print(f"Parsed {len(payment_data)} payment records from pasted data")
        else:
            # Load Excel file with payment data
            excel_file = input("Enter the path to your Excel file containing payment data: ")
            payment_data = load_excel_data(excel_file)
            print(f"Loaded {len(payment_data)} payment records")
        
        # Show configuration summary
        print("\nProgram Configuration:")
        print(f"Source Wallet: {source_wallet['address']}")
        print(f"Payment records: {len(payment_data)}")
        print(f"Each transaction will be scheduled {TICK_ADVANCE} ticks ahead of current network tick")
        print(f"The program will wait for each transaction to be confirmed before proceeding to the next one")
        
        # Show sample of payments
        print("\nSample of payments to be processed:")
        for i, payment in enumerate(payment_data[:5]):
            print(f"  {i+1}. Address: {payment['wallet_address']}, Amount: {payment['amount']} QUS")
        
        if len(payment_data) > 5:
            print(f"  ...and {len(payment_data) - 5} more")
        
        proceed = input("\nProceed with these settings? (y/n): ")
        if proceed.lower() != 'y':
            print("Program terminated by user")
            exit()
        
        # Create and run the sender
        sender = QUSSender(source_wallet, payment_data)
        sender.run()
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Please enter valid values")
        exit(1)
