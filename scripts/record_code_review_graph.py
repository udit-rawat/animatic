#!/usr/bin/env python3
"""
Simulates `pip install code-review-graph` → `code-review-graph build` → AST tree.
Screen-record this terminal window (4 seconds of output).
"""
import time, sys

GREEN  = "\033[38;2;0;255;65m"
DIM    = "\033[38;2;80;80;80m"
WHITE  = "\033[38;2;220;220;220m"
CYAN   = "\033[38;2;0;229;255m"
YELLOW = "\033[38;2;255;184;0m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def typewrite(text, delay=0.032, end="\n"):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(end)
    sys.stdout.flush()

def main():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    # Prompt + pip install
    print(f"{GREEN}❯{RESET} ", end="")
    typewrite("pip install code-review-graph", delay=0.045)
    time.sleep(0.2)

    pip_lines = [
        ("Collecting code-review-graph",                          0.15),
        ("  Downloading code_review_graph-0.4.1-py3-none-any.whl (38 kB)", 0.1),
        ("Collecting tree-sitter>=0.21.0 (from code-review-graph)", 0.08),
        ("  Downloading tree_sitter-0.21.3-cp311-cp311-macosx_arm64.whl (142 kB)", 0.07),
        ("Collecting networkx>=3.1 (from code-review-graph)",     0.07),
        ("  Downloading networkx-3.3-py3-none-any.whl (1.7 MB)",  0.06),
        ("Installing collected packages: tree-sitter, networkx, code-review-graph", 0.12),
        (f"Successfully installed code-review-graph-0.4.1  {GREEN}✓{RESET}", 0.2),
    ]
    for line, delay in pip_lines:
        print(f"{DIM}{line}{RESET}")
        time.sleep(delay)

    print()
    time.sleep(0.3)

    # Prompt + build command
    print(f"{GREEN}❯{RESET} ", end="")
    typewrite("code-review-graph build --path ./src", delay=0.045)
    time.sleep(0.25)

    print(f"{DIM}● Parsing source tree...{RESET}")
    time.sleep(0.2)
    print(f"{DIM}● Running tree-sitter AST extraction...{RESET}")
    time.sleep(0.25)
    print(f"{DIM}● Building symbol dependency graph...{RESET}\n")
    time.sleep(0.2)

    # AST tree output
    tree_lines = [
        (f"{CYAN}src/{RESET}",                                                                  0.06),
        (f"├── {WHITE}auth/{RESET}",                                                            0.05),
        (f"│   ├── {GREEN}middleware.ts{RESET}   {DIM}[12 exports · 3 deps]{RESET}",           0.05),
        (f"│   └── {GREEN}jwt.ts{RESET}          {DIM}[4 exports  · 1 dep ]{RESET}",           0.05),
        (f"├── {WHITE}core/{RESET}",                                                            0.05),
        (f"│   ├── {GREEN}knowledge_graph.ts{RESET}  {DIM}[8 exports  · 6 deps]{RESET}",       0.05),
        (f"│   ├── {GREEN}parser.ts{RESET}           {DIM}[5 exports  · 4 deps]{RESET}",       0.05),
        (f"│   └── {GREEN}resolver.ts{RESET}         {DIM}[7 exports  · 5 deps]{RESET}",       0.05),
        (f"├── {WHITE}db/{RESET}",                                                              0.05),
        (f"│   ├── {GREEN}queries.ts{RESET}      {DIM}[22 exports · 2 deps]{RESET}",           0.05),
        (f"│   └── {GREEN}schema.ts{RESET}       {DIM}[9 exports  · 1 dep ]{RESET}",           0.05),
        (f"└── {WHITE}retrieval/{RESET}",                                                       0.05),
        (f"    ├── {GREEN}bm25.ts{RESET}         {DIM}[3 exports  · 2 deps]{RESET}",           0.05),
        (f"    └── {GREEN}semantic.ts{RESET}     {DIM}[5 exports  · 4 deps]{RESET}",           0.05),
    ]

    for line, delay in tree_lines:
        print(f"  {line}")
        sys.stdout.flush()
        time.sleep(delay)

    print()
    time.sleep(0.1)
    print(f"  {DIM}{'─'*58}{RESET}")
    print(f"  {GREEN}✓{RESET}  {WHITE}50 files  ·  148 symbols  ·  {BOLD}{GREEN}graph cached to .crg/{RESET}")
    time.sleep(0.3)
    print(f"  {GREEN}✓{RESET}  {CYAN}Next run: only changed files re-parsed{RESET}")
    time.sleep(1.2)

if __name__ == "__main__":
    main()
