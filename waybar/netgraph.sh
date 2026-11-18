#!/bin/bash
iface=$(ip route | awk '/default/ {print $5; exit}')
stat=/sys/class/net/$iface/statistics
blocks=(▁ ▂ ▃ ▄ ▅ ▆ ▇ █)
n=10
floor=$((10*1024))
rx=(); tx=()
for ((k=0; k<n; k++)); do rx+=(0); tx+=(0); done
prx=$(<$stat/rx_bytes); ptx=$(<$stat/tx_bytes)

graph() {
  local max=$floor v out=""
  for v in "$@"; do ((v>max)) && max=$v; done
  for v in "$@"; do out+="${blocks[$((v*7/max))]}"; done
  echo "$out"
}
speed() {
  awk -v b=$1 'BEGIN {
    if (b>=1048576) printf "%.1f MB/s", b/1048576
    else if (b>=1024) printf "%.0f KB/s", b/1024
    else printf "%d B/s", b }'
}

while sleep 1; do
  crx=$(<$stat/rx_bytes); ctx=$(<$stat/tx_bytes)
  drx=$((crx-prx)); dtx=$((ctx-ptx)); prx=$crx; ptx=$ctx
  rx=("${rx[@]:1}" $drx)
  tx=("${tx[@]:1}" $dtx)
  printf '󰇚 %s %10s  󰕒 %s %10s\n' \
    "$(graph "${rx[@]}")" "$(speed $drx)" \
    "$(graph "${tx[@]}")" "$(speed $dtx)"
done
