import os
import sys
from typing import List, Dict

def verify_environment_integrity(required_keys: List[str]) -> Dict[str, str]:
    """Forensically scans active system variables, blocking boots on config leaks."""
    print("[+] Executing Sovereign Environment Validation Shield...")
    missing_parameters = []
    active_config = {}
    
    for key in required_keys:
        value = os.environ.get(key)
        if not value or value.strip() == "":
            missing_parameters.append(key)
        else:
            active_config[key] = value.strip()
            
    if missing_parameters:
        print(f"[!] SYSTEM INGESTION FAILURE: Missing Critical Keys -> {missing_parameters}")
        sys.exit(1) # Absolute defensive boot blockage
        
    print("[✔] Environment structure certified sterile. Boot corridor open.")
    return active_config

