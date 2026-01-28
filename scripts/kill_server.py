import subprocess
import os
import signal
import sys

def kill_process_on_port(port):
    print(f"Looking for process on port {port}...")
    try:
        # Check for processes on the port using lsof
        # -t: terse mode (only PIDs)
        # -i: select internet address matching
        cmd = f"lsof -t -i:{port}"
        # using shell=True to allow pipe if needed, but here simple execution is enough
        output = subprocess.check_output(cmd, shell=True)
        
        pids = output.decode().strip().split('\n')
        
        if not pids or pids == ['']:
            print(f"No process found listening on port {port}.")
            return

        for pid_str in pids:
            try:
                pid = int(pid_str)
                print(f"Found process PID: {pid}. Terminating...")
                os.kill(pid, signal.SIGKILL)
                print("Process killed.")
            except ValueError:
                continue
            except ProcessLookupError:
                print(f"Process {pid} already gone.")
            except Exception as e:
                print(f"Failed to kill {pid}: {e}")
                
    except subprocess.CalledProcessError:
        print(f"No process found listening on port {port}.")
    except Exception as e:
        print(f"Error checking port: {e}")

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number.")
            exit(1)
            
    kill_process_on_port(port)
