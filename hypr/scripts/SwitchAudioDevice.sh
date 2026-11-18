#!/usr/bin/env bash

CURRENT_SINK=$(pactl get-default-sink)
SINKS=($(pactl list short sinks | awk '{print $2}'))

for i in "${!SINKS[@]}"; do
    if [[ "${SINKS[$i]}" == "$CURRENT_SINK" ]]; then
        NEXT_INDEX=$(( (i + 1) % ${#SINKS[@]} ))
        NEXT_SINK="${SINKS[$NEXT_INDEX]}"
        break
    fi
done

pactl set-default-sink "$NEXT_SINK"

# Move active streams to new sink
for INPUT in $(pactl list short sink-inputs | awk '{print $1}'); do
    pactl move-sink-input "$INPUT" "$NEXT_SINK"
done

notify-send -u low "Audio Output" "Switched to: $NEXT_SINK"
