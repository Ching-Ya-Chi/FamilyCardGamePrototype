"""Run a small local demo for the CCG prototype.

Usage examples (from repository root):
    # default: launch the Tkinter client (login UI)
  python scripts/run_demo.py

  # start only the central server in a new process
  python scripts/run_demo.py --mode server

  # run the Tkinter client (single window)
  python scripts/run_demo.py --mode tkclient

Options:
  --listen-port / --connect-port - ports used for the responder and initiator

This script spawns subprocesses using the same Python interpreter. It doesn't daemonize
or manage complex lifecycles — it's a convenient developer helper to open the UI quickly.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]


def run_server():
    print('Starting central server (stdout/stderr forwarded)...')
    cmd = [sys.executable, str(ROOT / 'src' / 'server' / 'server_main.py')]
    env = os.environ.copy()
    # ensure project root is on PYTHONPATH so scripts using 'src' imports resolve
    env_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env_pythonpath if env_pythonpath else '')
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def run_pygame_responder(port: int):
    cmd = [sys.executable, str(ROOT / 'client' / 'battle_pygame.py'), '--listen', str(port)]
    print('Launching PyGame responder on port', port)
    env = os.environ.copy()
    env_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env_pythonpath if env_pythonpath else '')
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def run_pygame_initiator(ip: str, port: int):
    cmd = [sys.executable, str(ROOT / 'client' / 'battle_pygame.py'), '--connect', f"{ip}:{port}"]
    print('Launching PyGame initiator connecting to', ip, port)
    env = os.environ.copy()
    env_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env_pythonpath if env_pythonpath else '')
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def run_tk_client():
    cmd = [sys.executable, str(ROOT / 'client' / 'main.py')]
    print('Launching Tkinter client (single window)')
    env = os.environ.copy()
    env_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = str(ROOT) + (os.pathsep + env_pythonpath if env_pythonpath else '')
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['local-battle', 'server', 'tkclient'], default='tkclient')
    p.add_argument('--listen-port', type=int, default=6001)
    p.add_argument('--connect-ip', type=str, default='127.0.0.1')
    p.add_argument('--connect-port', type=int, default=6001)
    args = p.parse_args()

    procs = []
    try:
        if args.mode == 'server':
            p = run_server()
            procs.append(p)
            print('Server started. Press Ctrl-C to stop.')
            p.wait()

        elif args.mode == 'tkclient':
            p = run_tk_client()
            procs.append(p)
            p.wait()

        else:  # local-battle
            # Start a responder and then an initiator connecting to it. These are independent
            # processes that open PyGame windows. The order matters: start the listener first.
            resp = run_pygame_responder(args.listen_port)
            procs.append(resp)
            # give the responder a moment to set up
            time.sleep(0.6)
            init = run_pygame_initiator(args.connect_ip, args.connect_port)
            procs.append(init)

            print('Launched two PyGame clients for a local P2P battle. Close the windows to exit.')

            # Wait until both processes exit (or until interrupted)
            while True:
                alive = [p.poll() is None for p in procs]
                if not any(alive):
                    break
                time.sleep(0.5)

    except KeyboardInterrupt:
        print('Interrupted — terminating child processes...')
    finally:
        for p in procs:
            try:
                if p.poll() is None:
                    p.terminate()
            except Exception:
                pass


if __name__ == '__main__':
    main()
