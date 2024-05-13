#!/usr/bin/env bash

# List of servers to check for network connectivity
servers=("8.8.8.8" "1.1.1.1" "208.67.222.222") # Google, Cloudflare, OpenDNS

# Function to check network connectivity
check_network() {
    for server in "${servers[@]}"; do
        if ping -c 1 "$server" > /dev/null 2>&1; then
            return 0 # Network is available
        fi
    done
    return 1 # Network is not available
}

# Keep checking for network availability
until check_network
do
    echo "Waiting for network..."
    sleep 1
done

echo "Network is available..."
exit 0
