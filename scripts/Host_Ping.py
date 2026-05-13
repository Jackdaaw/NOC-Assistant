import os
import platform
import subprocess
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

input_file = "Hosts.txt"

now = datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H-%M")
output_file = f"IP_Status_{timestamp}.txt"
error_log_file = f"IP_ErrorLog_{timestamp}.txt"

IP_V4_REGEX = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

def is_valid_ipv4(ip: str) -> bool:
    if not IP_V4_REGEX.match(ip):
        return False
    parts = ip.split(".")
    for p in parts:
        n = int(p)
        if n < 0 or n > 255:
            return False
    return True

def ping_ip(ip: str, name: str):
    """
    Returns tuple: (ip, name, status, ping_time_or_dash, error_or_none)
    """
    param = "-n" if platform.system().lower() == "windows" else "-c"
    count = "4"

    try:
        result = subprocess.run(
            ["ping", param, count, ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        out = result.stdout.lower()

        if ("unreachable" in out) or (result.returncode != 0):
            return (ip, name, "Down", "-", None)

        avg_time = "-"
        if "average =" in out:
            try:
                avg_time = out.split("average =")[-1].split("ms")[0].strip()
            except:
                avg_time = "-"
        else:
            if "/" in out and "min/avg/max" in out:
                try:
                    last_line = out.strip().splitlines()[-1]
                except:
                    avg_time = "-"
            if avg_time == "-":
                try:
                    tokens = out.replace("ms", " ").split("/")
                    if len(tokens) >= 4:
                        avg_time = tokens[-3].strip()
                except:
                    avg_time = "-"

        return (ip, name, "Up", avg_time, None)

    except subprocess.TimeoutExpired:
        return (ip, name, "Down", "-", "Ping Timeout")
    except Exception as e:
        return (ip, name, "Down", "-", f"Ping Error: {type(e).__name__}")

def main():
    if not os.path.exists(input_file):
        print("File Not Found")
        return

    results = []
    down_ips_print_block = []

    error_lines = []

    with open(input_file, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip()]

    entries = []
    for line in raw_lines:
        try:
            ip, name = line.split(",", 1)
            ip = ip.strip()
            name = name.strip()
        except ValueError:
            print("Wrong Format In Line")
            error_lines.append(f"{line} | Wrong Format In Line")
            continue

        if not is_valid_ipv4(ip) or not name:
            print("Wrong Format In Line")
            error_lines.append(f"{ip}, {name} | Invalid IP or Empty Name")
            continue

        entries.append((ip, name))

    if not entries:
        with open(output_file, "w", encoding="utf-8") as out:
            out.write("IP, Name, Status, Date, Time, Ping Time\n")

        with open(error_log_file, "w", encoding="utf-8") as el:
            el.write("Error Log\n")
            if error_lines:
                el.write("\n".join(error_lines))
        print("All Hosts Is Up")
        print("Result Saved")
        return

    max_workers = 30
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(ping_ip, ip, name): (ip, name)
            for ip, name in entries
        }

        for future in as_completed(futures):
            ip, name = futures[future]
            try:
                ip, name, status, ping_time, err = future.result()
            except Exception as e:
                status, ping_time = "Down", "-"
                err = f"Worker Exception: {type(e).__name__}"

            results.append(f"{ip}, {name}, {status}, {date}, {time}, {ping_time}")

            if status == "Down":
                down_ips_print_block.append(f"{ip}, {name}, Down")

            if err:
                error_lines.append(f"{ip}, {name} | {err}")

    with open(output_file, "w", encoding="utf-8") as out:
        out.write("IP, Name, Status, Date, Time, Ping Time\n")
        out.write("\n".join(results))

    with open(error_log_file, "w", encoding="utf-8") as el:
        el.write("Error Log\n")
        if error_lines:
            el.write("\n".join(error_lines))

    if down_ips_print_block:
        print("Hosts Down")
        for item in down_ips_print_block:
            print(item)
    else:
        print("All Hosts Is Up")

    print("Result Saved")

if __name__ == "__main__":
    main()
