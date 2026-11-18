#!/usr/bin/env bash
WALLPAPER=$(cat ~/.config/hypr/wallpaper_effects/.wallpaper_current)
sleep 1
swww img --outputs HDMI-A-1 "$WALLPAPER" --transition-type fade --transition-duration 1
swww img --outputs eDP-1 "$WALLPAPER" --transition-type fade --transition-duration 1
