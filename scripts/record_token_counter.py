#!/usr/bin/env python3
"""
Simulates token count dropping: 13,240 → 1,608 (8.2x reduction).
6 seconds. Screen-record this terminal window.
"""
import time, sys, math

GREEN  = "\033[38;2;0;255;65m"
RED    = "\033[38;2;229;72;77m"
DIM    = "\033[38;2;80;80;80m"
WHITE  = "\033[38;2;220;220;220m"
CYAN   = "\033[38;2;0;229;255m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

CURSOR_UP   = "\033[A"
CURSOR_COL0 = "\033[0G"
ERASE_LINE  = "\033[2K"

def format_bar(ratio, width=32):
    filled = int(ratio * width)
    return f"{'█' * filled}{'░' * (width - filled)}"

def main():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    START  = 13240
    END    = 1608
    FRAMES = 80   # animation frames over ~4s

    print(f"{BOLD}{WHITE}Token Footprint Analyzer{RESET}  {DIM}— code-review-graph{RESET}\n")
    time.sleep(0.3)

    print(f"  {DIM}Mode:{RESET}  {WHITE}Naïve (send full repo){RESET}")
    time.sleep(0.15)
    print(f"  {DIM}Repo:{RESET}  {WHITE}./src  (50 files){RESET}\n")
    time.sleep(0.4)

    # Static before line
    print(f"  {DIM}Before  {RESET}{RED}{START:>7,} tokens{RESET}  {RED}{format_bar(1.0)}{RESET}")
    time.sleep(0.5)

    # After line — will animate in place
    print(f"  {DIM}After   {RESET}{WHITE}{START:>7,} tokens{RESET}  {GREEN}{format_bar(1.0)}{RESET}")
    sys.stdout.flush()
    time.sleep(0.1)

    # Animate the "After" line downward
    for i in range(FRAMES + 1):
        t = i / FRAMES
        # ease-out cubic
        ease = 1 - (1 - t) ** 3
        current = int(START + (END - START) * ease)
        ratio = current / START

        color = GREEN if ratio < 0.3 else (CYAN if ratio < 0.6 else WHITE)
        bar   = format_bar(ratio)

        sys.stdout.write(CURSOR_UP + CURSOR_COL0 + ERASE_LINE)
        sys.stdout.write(f"  {DIM}After   {RESET}{color}{BOLD}{current:>7,} tokens{RESET}  {GREEN}{bar}{RESET}")
        sys.stdout.flush()
        time.sleep(0.048)

    print()  # newline after animation
    time.sleep(0.3)

    reduction = START / END
    savings   = START - END

    print()
    print(f"  {DIM}{'─'*58}{RESET}")
    print(f"  {GREEN}✓{RESET}  {BOLD}{WHITE}Reduction:{RESET}  {GREEN}{BOLD}{reduction:.1f}x fewer tokens{RESET}")
    time.sleep(0.2)
    print(f"  {GREEN}✓{RESET}  {WHITE}Saved:    {RESET}  {GREEN}{savings:,} tokens per review call{RESET}")
    time.sleep(0.2)
    print(f"  {GREEN}✓{RESET}  {CYAN}Graph hit rate:  94%  (AST cache warm){RESET}")
    time.sleep(1.5)

if __name__ == "__main__":
    main()
