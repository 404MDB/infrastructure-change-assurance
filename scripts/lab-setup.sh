#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run this script with sudo." >&2
    exit 1
fi

if [[ $(hostname) != "debian-control" ]]; then
    echo "Run this lab setup on debian-control." >&2
    exit 1
fi

for tool in ip ping; do
    command -v "$tool" >/dev/null || {
        echo "Missing required command: $tool" >&2
        exit 1
    }
done

for ns in ica-client ica-lab; do
    if ip netns list | awk '{print $1}' | grep -Fxq "$ns"; then
        echo "$ns already exists; inspect it before continuing." >&2
        exit 1
    fi
done

for link in veth-client veth-server; do
    if ip link show dev "$link" >/dev/null 2>&1; then
        echo "$link already exists; stopping without changes." >&2
        exit 1
    fi
done

client_created=0
server_created=0
pair_created=0

cleanup_on_failure() {
    if (( client_created )); then
        ip netns delete ica-client || true
    fi
    if (( server_created )); then
        ip netns delete ica-lab || true
    fi
    if (( pair_created )); then
        ip link delete veth-client 2>/dev/null || true
    fi
}

trap cleanup_on_failure EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

ip netns add ica-client
client_created=1
ip netns add ica-lab
server_created=1

ip link add veth-client type veth peer name veth-server
pair_created=1
ip link set veth-client netns ica-client
ip link set veth-server netns ica-lab

ip -n ica-client address add 10.200.1.1/24 dev veth-client
ip -n ica-lab address add 10.200.1.2/24 dev veth-server

ip -n ica-client link set lo up
ip -n ica-lab link set lo up
ip -n ica-client link set veth-client up
ip -n ica-lab link set veth-server up

ip netns exec ica-client ping -c 3 -W 2 10.200.1.2

trap - EXIT INT TERM
echo "Lab ready: ica-client (10.200.1.1) -> ica-lab (10.200.1.2)"
