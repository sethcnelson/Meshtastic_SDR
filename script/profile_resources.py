#!/usr/bin/env python3
"""
Resource profiler for Meshtastic SDR stack.
Run inside Docker container to measure CPU, memory, I/O patterns.
Outputs CSV data for analysis and Pi deployment forecasting.

Usage:
    python3 profile_resources.py [duration_minutes]

Example:
    python3 profile_resources.py 60  # Profile for 1 hour
"""

import subprocess
import time
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Sampling interval in seconds
SAMPLE_INTERVAL = 5

def get_process_stats(pid):
    """Get CPU and memory stats for a process from /proc."""
    try:
        # Memory from /proc/PID/status
        status_path = f"/proc/{pid}/status"
        stat_path = f"/proc/{pid}/stat"

        if not os.path.exists(status_path):
            return None

        stats = {
            'pid': pid,
            'rss_mb': 0,
            'vms_mb': 0,
            'cpu_percent': 0,
            'threads': 0,
            'name': ''
        }

        # Parse /proc/PID/status for memory
        with open(status_path, 'r') as f:
            for line in f:
                if line.startswith('Name:'):
                    stats['name'] = line.split(':')[1].strip()
                elif line.startswith('VmRSS:'):
                    stats['rss_mb'] = int(line.split()[1]) / 1024
                elif line.startswith('VmSize:'):
                    stats['vms_mb'] = int(line.split()[1]) / 1024
                elif line.startswith('Threads:'):
                    stats['threads'] = int(line.split()[1])

        # Parse /proc/PID/stat for CPU time
        with open(stat_path, 'r') as f:
            parts = f.read().split()
            stats['utime'] = int(parts[13])  # User time
            stats['stime'] = int(parts[14])  # System time

        return stats
    except (FileNotFoundError, PermissionError, IndexError):
        return None


def find_target_processes():
    """Find GNU Radio and Python decoder processes."""
    processes = {}

    try:
        # Use pgrep to find relevant processes
        result = subprocess.run(
            ['ps', 'aux'], capture_output=True, text=True
        )

        for line in result.stdout.split('\n')[1:]:
            if not line.strip():
                continue
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue

            pid = int(parts[1])
            cmd = parts[10]

            # Identify our processes
            if 'python' in cmd.lower():
                if 'main.py' in cmd:
                    processes[pid] = 'decoder'
                elif 'app.py' in cmd or 'flask' in cmd.lower():
                    processes[pid] = 'webui'
                elif 'meshtastic' in cmd.lower() or 'lora' in cmd.lower():
                    processes[pid] = 'gnuradio'
            elif 'gnuradio' in cmd.lower() or 'gr-' in cmd.lower():
                processes[pid] = 'gnuradio'

    except Exception as e:
        print(f"Error finding processes: {e}")

    return processes


def get_system_stats():
    """Get overall system CPU and memory."""
    stats = {
        'cpu_percent': 0,
        'mem_total_mb': 0,
        'mem_available_mb': 0,
        'mem_used_mb': 0,
        'load_1m': 0,
        'load_5m': 0,
        'load_15m': 0
    }

    # CPU from /proc/stat
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            parts = line.split()[1:]
            # Returns cumulative values, we'll calculate delta later
            stats['cpu_total'] = sum(int(p) for p in parts[:7])
            stats['cpu_idle'] = int(parts[3])
    except:
        pass

    # Memory from /proc/meminfo
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(':')
                value = int(parts[1])
                meminfo[key] = value

            stats['mem_total_mb'] = meminfo.get('MemTotal', 0) / 1024
            stats['mem_available_mb'] = meminfo.get('MemAvailable', 0) / 1024
            stats['mem_used_mb'] = stats['mem_total_mb'] - stats['mem_available_mb']
    except:
        pass

    # Load average
    try:
        with open('/proc/loadavg', 'r') as f:
            parts = f.read().split()
            stats['load_1m'] = float(parts[0])
            stats['load_5m'] = float(parts[1])
            stats['load_15m'] = float(parts[2])
    except:
        pass

    return stats


def get_io_stats():
    """Get disk I/O statistics."""
    stats = {'read_bytes': 0, 'write_bytes': 0}

    try:
        with open('/proc/diskstats', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 14:
                    # Sum all disk reads/writes (sectors * 512 bytes)
                    stats['read_bytes'] += int(parts[5]) * 512
                    stats['write_bytes'] += int(parts[9]) * 512
    except:
        pass

    return stats


def get_database_size():
    """Get mesh.db file size."""
    db_paths = [
        '/app/mesh.db',
        './mesh.db',
        '../mesh.db',
        '/data/mesh.db'
    ]

    for path in db_paths:
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            return {'path': path, 'size_mb': size_mb}

    return {'path': None, 'size_mb': 0}


def main():
    duration_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    duration_seconds = duration_minutes * 60

    print(f"=== Meshtastic SDR Resource Profiler ===")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Sample interval: {SAMPLE_INTERVAL} seconds")
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Output file
    output_dir = Path(__file__).parent.parent / 'logs'
    output_dir.mkdir(exist_ok=True)
    csv_path = output_dir / f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Find processes
    target_procs = find_target_processes()
    print(f"Found processes: {target_procs}")
    print()

    # CSV header
    with open(csv_path, 'w') as f:
        f.write("timestamp,elapsed_sec,")
        f.write("sys_cpu_percent,sys_mem_used_mb,sys_mem_total_mb,load_1m,")
        f.write("decoder_rss_mb,decoder_cpu_pct,")
        f.write("webui_rss_mb,webui_cpu_pct,")
        f.write("gnuradio_rss_mb,gnuradio_cpu_pct,")
        f.write("db_size_mb,io_read_mb,io_write_mb\n")

    # Previous values for delta calculations
    prev_cpu = None
    prev_io = None
    prev_proc_cpu = {}

    start_time = time.time()
    samples = []

    print("Sampling... (Ctrl+C to stop early)")
    print("-" * 60)

    try:
        while time.time() - start_time < duration_seconds:
            now = datetime.now()
            elapsed = time.time() - start_time

            # System stats
            sys_stats = get_system_stats()
            io_stats = get_io_stats()
            db_info = get_database_size()

            # Calculate CPU percentage
            cpu_percent = 0
            if prev_cpu is not None:
                total_delta = sys_stats['cpu_total'] - prev_cpu['total']
                idle_delta = sys_stats['cpu_idle'] - prev_cpu['idle']
                if total_delta > 0:
                    cpu_percent = 100 * (1 - idle_delta / total_delta)
            prev_cpu = {'total': sys_stats['cpu_total'], 'idle': sys_stats['cpu_idle']}

            # Calculate I/O rates
            io_read_mb = 0
            io_write_mb = 0
            if prev_io is not None:
                io_read_mb = (io_stats['read_bytes'] - prev_io['read']) / (1024 * 1024)
                io_write_mb = (io_stats['write_bytes'] - prev_io['write']) / (1024 * 1024)
            prev_io = {'read': io_stats['read_bytes'], 'write': io_stats['write_bytes']}

            # Process stats
            proc_stats = {'decoder': {}, 'webui': {}, 'gnuradio': {}}

            # Re-scan for processes (they might restart)
            target_procs = find_target_processes()

            for pid, ptype in target_procs.items():
                pstat = get_process_stats(pid)
                if pstat:
                    # Calculate per-process CPU
                    proc_cpu = 0
                    cpu_key = f"{ptype}_{pid}"
                    current_time = pstat['utime'] + pstat['stime']
                    if cpu_key in prev_proc_cpu:
                        time_delta = current_time - prev_proc_cpu[cpu_key]
                        # Approximate: divide by sample interval in jiffies (100 Hz typical)
                        proc_cpu = (time_delta / (SAMPLE_INTERVAL * 100)) * 100
                    prev_proc_cpu[cpu_key] = current_time

                    if ptype not in proc_stats or not proc_stats[ptype]:
                        proc_stats[ptype] = {'rss_mb': 0, 'cpu_pct': 0}
                    proc_stats[ptype]['rss_mb'] += pstat['rss_mb']
                    proc_stats[ptype]['cpu_pct'] += proc_cpu

            # Build sample
            sample = {
                'timestamp': now.isoformat(),
                'elapsed_sec': int(elapsed),
                'sys_cpu_percent': round(cpu_percent, 1),
                'sys_mem_used_mb': round(sys_stats['mem_used_mb'], 1),
                'sys_mem_total_mb': round(sys_stats['mem_total_mb'], 1),
                'load_1m': round(sys_stats['load_1m'], 2),
                'decoder_rss_mb': round(proc_stats.get('decoder', {}).get('rss_mb', 0), 1),
                'decoder_cpu_pct': round(proc_stats.get('decoder', {}).get('cpu_pct', 0), 1),
                'webui_rss_mb': round(proc_stats.get('webui', {}).get('rss_mb', 0), 1),
                'webui_cpu_pct': round(proc_stats.get('webui', {}).get('cpu_pct', 0), 1),
                'gnuradio_rss_mb': round(proc_stats.get('gnuradio', {}).get('rss_mb', 0), 1),
                'gnuradio_cpu_pct': round(proc_stats.get('gnuradio', {}).get('cpu_pct', 0), 1),
                'db_size_mb': round(db_info['size_mb'], 2),
                'io_read_mb': round(io_read_mb, 2),
                'io_write_mb': round(io_write_mb, 2)
            }
            samples.append(sample)

            # Write to CSV
            with open(csv_path, 'a') as f:
                f.write(f"{sample['timestamp']},{sample['elapsed_sec']},")
                f.write(f"{sample['sys_cpu_percent']},{sample['sys_mem_used_mb']},{sample['sys_mem_total_mb']},{sample['load_1m']},")
                f.write(f"{sample['decoder_rss_mb']},{sample['decoder_cpu_pct']},")
                f.write(f"{sample['webui_rss_mb']},{sample['webui_cpu_pct']},")
                f.write(f"{sample['gnuradio_rss_mb']},{sample['gnuradio_cpu_pct']},")
                f.write(f"{sample['db_size_mb']},{sample['io_read_mb']},{sample['io_write_mb']}\n")

            # Print status
            print(f"[{now.strftime('%H:%M:%S')}] CPU: {sample['sys_cpu_percent']:5.1f}% | "
                  f"Mem: {sample['sys_mem_used_mb']:.0f}/{sample['sys_mem_total_mb']:.0f} MB | "
                  f"Load: {sample['load_1m']:.2f} | "
                  f"GR: {sample['gnuradio_rss_mb']:.0f}MB | "
                  f"Dec: {sample['decoder_rss_mb']:.0f}MB | "
                  f"DB: {sample['db_size_mb']:.1f}MB")

            time.sleep(SAMPLE_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nStopped early by user.")

    # Summary - build as string to write to both stdout and file
    summary_lines = []
    summary_lines.append("")
    summary_lines.append("=" * 60)
    summary_lines.append("PROFILING SUMMARY")
    summary_lines.append("=" * 60)

    if samples:
        # Calculate averages and peaks
        def avg(key):
            return sum(s[key] for s in samples) / len(samples)
        def peak(key):
            return max(s[key] for s in samples)

        summary_lines.append(f"\nDuration: {len(samples) * SAMPLE_INTERVAL / 60:.1f} minutes ({len(samples)} samples)")
        summary_lines.append(f"\nSystem Resources:")
        summary_lines.append(f"  CPU:     avg {avg('sys_cpu_percent'):.1f}%  peak {peak('sys_cpu_percent'):.1f}%")
        summary_lines.append(f"  Memory:  avg {avg('sys_mem_used_mb'):.0f} MB  peak {peak('sys_mem_used_mb'):.0f} MB")
        summary_lines.append(f"  Load:    avg {avg('load_1m'):.2f}  peak {peak('load_1m'):.2f}")

        summary_lines.append(f"\nPer-Process Memory (RSS):")
        summary_lines.append(f"  GNU Radio: avg {avg('gnuradio_rss_mb'):.0f} MB  peak {peak('gnuradio_rss_mb'):.0f} MB")
        summary_lines.append(f"  Decoder:   avg {avg('decoder_rss_mb'):.0f} MB  peak {peak('decoder_rss_mb'):.0f} MB")
        summary_lines.append(f"  WebUI:     avg {avg('webui_rss_mb'):.0f} MB  peak {peak('webui_rss_mb'):.0f} MB")

        total_mem = avg('gnuradio_rss_mb') + avg('decoder_rss_mb') + avg('webui_rss_mb')
        summary_lines.append(f"  TOTAL:     ~{total_mem:.0f} MB average")

        summary_lines.append(f"\nDatabase:")
        summary_lines.append(f"  Final size: {samples[-1]['db_size_mb']:.2f} MB")
        if samples[0]['db_size_mb'] > 0:
            growth = samples[-1]['db_size_mb'] - samples[0]['db_size_mb']
            summary_lines.append(f"  Growth:     {growth:.2f} MB during profiling")

        summary_lines.append(f"\nRaspberry Pi Recommendation:")
        if total_mem < 400:
            summary_lines.append(f"  ✓ Pi 4 (2GB) should work for headless operation")
        elif total_mem < 800:
            summary_lines.append(f"  ✓ Pi 4 (4GB) recommended")
        else:
            summary_lines.append(f"  ⚠ Pi 5 (8GB) recommended due to high memory usage")

        if peak('sys_cpu_percent') < 50:
            summary_lines.append(f"  ✓ CPU usage is low, any Pi 4/5 should handle it")
        elif peak('sys_cpu_percent') < 75:
            summary_lines.append(f"  ✓ Pi 4 should handle this, Pi 5 gives headroom")
        else:
            summary_lines.append(f"  ⚠ High CPU usage - consider reducing decoder chains or use Pi 5")

        summary_lines.append(f"\nCSV output: {csv_path}")

        # Write summary to file
        summary_path = csv_path.with_suffix('.summary.txt')
        summary_lines.append(f"Summary output: {summary_path}")

        with open(summary_path, 'w') as f:
            f.write('\n'.join(summary_lines))
            f.write('\n')

    # Print summary to stdout
    for line in summary_lines:
        print(line)
    print()


if __name__ == '__main__':
    main()
