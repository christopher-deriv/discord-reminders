import time
import hashlib
import urllib.request
import urllib.parse
import json
import sys
import argparse
import random

# Constants
API_BASE_URL = "https://kingshot-giftcode.centurygame.com/api"
SALT = "mN4!pQs6JrYwV9"

# Common headers to mimic official web browser requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://ks-giftcode.centurygame.com",
    "Referer": "https://ks-giftcode.centurygame.com/",
    "Connection": "keep-alive"
}

def generate_signature(params: dict) -> str:
    """
    Generates the MD5 signature for Century Games / KingShot gift code API requests.
    Sorts keys alphabetically, formats as a query string, appends the secret salt,
    and calculates the MD5 hash.
    """
    sorted_keys = sorted(params.keys())
    param_pairs = []
    for key in sorted_keys:
        param_pairs.append(f"{key}={params[key]}")
    param_string = "&".join(param_pairs)
    string_to_hash = f"{param_string}{SALT}"
    return hashlib.md5(string_to_hash.encode("utf-8")).hexdigest()

def make_post_request(endpoint: str, data: dict) -> dict:
    """
    Makes a POST request to the specified KingShot API endpoint with URL-encoded body.
    """
    url = f"{API_BASE_URL}/{endpoint}"
    
    if "time" not in data:
        data["time"] = str(int(time.time() * 1000))
    if "sign" not in data:
        data["sign"] = generate_signature(data)
        
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data)
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def verify_player(fid: str) -> dict:
    """
    Queries the KingShot API to fetch details about a player by Player ID (fid).
    """
    payload = {"fid": str(fid)}
    return make_post_request("player", payload)

def redeem_code(fid: str, cdk: str) -> dict:
    """
    Redeems a gift code (cdk) for a given Player ID (fid).
    """
    payload = {
        "fid": str(fid),
        "cdk": str(cdk),
        "captcha_code": ""
    }
    return make_post_request("gift_code", payload)

def get_config() -> dict:
    """
    Queries the initial gift code configuration (e.g. active banners, localizations).
    """
    return make_post_request("gift_code_config", {})

def parse_list(input_str: str) -> list:
    """
    Parses a comma-separated or space-separated string into a list of clean strings.
    """
    if not input_str:
        return []
    raw_items = input_str.replace(",", " ").split()
    return [item.strip() for item in raw_items if item.strip()]

def parse_delay(delay_str: str):
    """
    Parses delay input. Can be a single float or a range 'min-max'.
    Returns a tuple (min_delay, max_delay) or a single float.
    """
    delay_str = delay_str.strip()
    if "-" in delay_str:
        try:
            parts = delay_str.split("-")
            min_val = float(parts[0].strip())
            max_val = float(parts[1].strip())
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            return (min_val, max_val)
        except ValueError:
            pass
    try:
        return float(delay_str)
    except ValueError:
        return (2.0, 5.0)

def execute_delay(delay_config):
    """
    Sleeps for a duration determined by the delay configuration.
    """
    if isinstance(delay_config, tuple):
        actual_delay = random.uniform(delay_config[0], delay_config[1])
        print(f"    [Anti-flag delay: sleeping for {actual_delay:.2f}s]")
        time.sleep(actual_delay)
    else:
        if delay_config > 0:
            print(f"    [Anti-flag delay: sleeping for {delay_config:.2f}s]")
            time.sleep(delay_config)

def get_delay_display(delay_config) -> str:
    if isinstance(delay_config, tuple):
        return f"Randomized range between {delay_config[0]} and {delay_config[1]} seconds"
    return f"Fixed {delay_config} seconds"

def main():
    print("=" * 65)
    print("      KINGSHOT MULTI-ACCOUNT GIFT CODE REDEMPTION SCRIPT")
    print("=" * 65)

    parser = argparse.ArgumentParser(description="Redeem KingShot Gift Codes for multiple players with rate-limiting delays.")
    parser.add_argument("--ids", type=str, help="Comma or space-separated list of Player IDs (FIDs)")
    parser.add_argument("--codes", type=str, help="Comma or space-separated list of Gift Codes (CDKs)")
    parser.add_argument("--delay", type=str, default="2-5", help="Delay config in seconds (default: '2-5' range)")
    args = parser.parse_args()

    # Interactive input if command-line arguments are missing
    if not args.ids or not args.codes:
        print("[*] Entering interactive mode...")
        raw_ids = input("Enter Player ID(s) (separated by commas or spaces): ").strip()
        raw_codes = input("Enter Gift Code(s) (separated by commas or spaces): ").strip()
        
        player_ids = parse_list(raw_ids)
        gift_codes = parse_list(raw_codes)
        # Automatically use 2-5s randomized range for interactive mode
        delay_config = (2.0, 5.0)
    else:
        player_ids = parse_list(args.ids)
        gift_codes = parse_list(args.codes)
        delay_config = parse_delay(args.delay)

    if not player_ids:
        print("[-] Error: At least one Player ID (FID) is required.")
        return
    if not gift_codes:
        print("[-] Error: At least one Gift Code (CDK) is required.")
        return

    print("\n[*] Initializing redemption queue:")
    print(f"    Player IDs ({len(player_ids)}): {', '.join(player_ids)}")
    print(f"    Gift Codes ({len(gift_codes)}): {', '.join(gift_codes)}")
    print(f"    Delay setting  : {get_delay_display(delay_config)} (Automatic)")
    print("-" * 65)

    # Mimic browser opening config
    config = get_config()
    if config.get("code") != 0:
        print("[-] Warning: Configuration check failed, proceeding anyway...")
    execute_delay(delay_config)

    for p_idx, fid in enumerate(player_ids):
        print(f"\n[{p_idx + 1}/{len(player_ids)}] Processing Player ID: {fid} ...")
        
        # 1. Verify Player details
        player_res = verify_player(fid)
        if player_res.get("code") != 0 or not player_res.get("data"):
            msg = player_res.get("msg", "Player not found or query error")
            print(f"  [-] Skip: Could not verify Player ID {fid}. Reason: {msg}")
            execute_delay(delay_config)
            continue

        player_data = player_res["data"]
        nickname = player_data.get("nickname", "Unknown")
        kid = player_data.get("kid", "N/A")
        stove_lv = player_data.get("stove_lv", "N/A")
        
        print(f"  [+] Player Verified: {nickname} (Kingdom #{kid}, Stove Level: {stove_lv})")
        
        # Introduce delay before moving to codes
        execute_delay(delay_config)

        # 2. Iterate through codes for this verified player
        for c_idx, cdk in enumerate(gift_codes):
            print(f"  [{c_idx + 1}/{len(gift_codes)}] Redeeming code '{cdk}'...")
            
            redeem_res = redeem_code(fid, cdk)
            code = redeem_res.get("code")
            msg = redeem_res.get("msg", "No response message")
            err_code = redeem_res.get("err_code")

            if code == 0:
                print(f"    [+] SUCCESS: Code '{cdk}' successfully redeemed!")
            elif code == 1 and err_code == 40008:
                print(f"    [!] Info: Code '{cdk}' has ALREADY been claimed on this account.")
            else:
                print(f"    [-] Failed: {msg} (Error Code: {err_code})")

            # Introduce delay between redemptions
            if not (p_idx == len(player_ids) - 1 and c_idx == len(gift_codes) - 1):
                execute_delay(delay_config)

    print("\n" + "=" * 65)
    print("      ALL QUEUED REDEMPTIONS COMPLETED")
    print("=" * 65)

if __name__ == "__main__":
    main()
