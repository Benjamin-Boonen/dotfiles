#!/usr/bin/env bash

WALLDIR="$HOME/Pictures/wallpapers"

# Pick wallpaper with wofi
WALLPAPER=$(find "$WALLDIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \) | wofi --dmenu --prompt "Wallpaper" --insensitive)

# Exit if nothing selected
[[ -z "$WALLPAPER" ]] && exit 0

# Set wallpaper on both monitors
swww img --outputs HDMI-A-1 "$WALLPAPER" --transition-type fade --transition-duration 1
swww img --outputs eDP-1 "$WALLPAPER" --transition-type fade --transition-duration 1

# Save current wallpaper
ln -sf "$WALLPAPER" $HOME/dotfiles/hypr/wallpaper_effects/.wallpaper_current

# Run wallust
wallust run "$WALLPAPER"
python3 "$HOME/dotfiles/hypr/scripts/fix_contrast.py" "$HOME/.config/kitty/kitty-themes/01-Wallust.conf"
# Reload everything
killall waybar; waybar &
hyprctl reload
makoctl reload
kill -USR1 $(pgrep kitty) 2>/dev/null
