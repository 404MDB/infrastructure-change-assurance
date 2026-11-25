#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-block-http}" in
    block-http|allow-http|invalid-syntax)
        CANDIDATE="$ROOT_DIR/config/candidates/${1:-block-http}.nft"
        ;;
    *)
        echo "Usage: sudo bash scripts/test-candidate.sh [block-http|allow-http|invalid-syntax]" >&2
        exit 2
        ;;
esac

if [[ $EUID -ne 0 || $(hostname) != "debian-control" ]]; then
    echo "Run with sudo on debian-control." >&2
    exit 2
fi

for tool in ip nft curl; do
    command -v "$tool" >/dev/null || {
        echo "Missing command: $tool" >&2
        exit 2
    }
done

ip netns exec ica-client true
ip netns exec ica-lab nft list ruleset >/dev/null

if ip netns exec ica-lab nft list table inet ica_candidate >/dev/null 2>&1; then
    echo "Candidate table already exists; inspect it first." >&2
    exit 2
fi

http_ok() {
    local status
    if status=$(ip netns exec ica-client curl --silent --show-error \
        --head --output /dev/null --write-out '%{http_code}' \
        --connect-timeout 3 --max-time 5 http://10.200.1.2/); then
        echo "HTTP status: $status"
        [[ $status == "200" ]]
    else
        echo "HTTP probe failed." >&2
        return 1
    fi
}

cleanup_needed=0
cleanup() {
    if (( cleanup_needed )); then
        if ip netns exec ica-lab nft delete table inet ica_candidate; then
            cleanup_needed=0
        else
            echo "CLEANUP FAILED: inspect ica-lab rules." >&2
            return 1
        fi
    fi
}

trap 'cleanup || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

emit_stage() {
    printf 'ICA_EVENT {"stage":"%s","status":"%s"}\n' "$1" "$2"
}

echo "1. Checking lab baseline"
if ! http_ok; then
    emit_stage baseline failed
    echo "ERROR: baseline unhealthy; candidate not applied."
    exit 2
fi
emit_stage baseline passed

echo "2. Validating candidate syntax"
if ! ip netns exec ica-lab nft -c -f "$CANDIDATE"; then
    emit_stage validation failed
    exit 2
fi
emit_stage validation passed

echo "3. Applying candidate inside ica-lab"
cleanup_needed=1
if ! ip netns exec ica-lab nft -f "$CANDIDATE"; then
    emit_stage apply failed
    exit 2
fi
emit_stage apply passed

echo "4. Checking candidate impact"
candidate_passed=0
if http_ok; then
    candidate_passed=1
    emit_stage impact passed
else
    emit_stage impact failed
fi
ip netns exec ica-lab nft list table inet ica_candidate

echo "5. Removing candidate"
if ! cleanup; then
    emit_stage cleanup failed
    exit 3
fi
emit_stage cleanup passed

echo "6. Checking recovery"
if ! http_ok; then
    emit_stage recovery failed
    echo "RECOVERY FAILED"
    exit 3
fi
emit_stage recovery passed

if (( candidate_passed )); then
    echo "CANDIDATE PASSED: required lab HTTP check preserved."
    exit 0
fi

echo "CANDIDATE BLOCKED: required lab HTTP check failed; recovery verified."
exit 1
