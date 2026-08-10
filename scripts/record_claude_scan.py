#!/usr/bin/env python3
"""
Simulates Claude scanning a codebase — 5 seconds of file reads flying by.
Screen-record this with QuickTime or run:
  python3 record_claude_scan.py
Then Cmd+Shift+5 to record the terminal window.
"""

import time, sys, random

GREEN = "\033[38;2;0;255;65m"
DIM = "\033[38;2;80;80;80m"
WHITE = "\033[38;2;220;220;220m"
CYAN = "\033[38;2;0;229;255m"
RESET = "\033[0m"
BOLD = "\033[1m"

FILES = [
    "src/auth/middleware.ts",
    "src/auth/jwt.ts",
    "src/db/queries.ts",
    "src/db/schema.ts",
    "src/api/routes.ts",
    "src/api/handlers.ts",
    "src/utils/tokenizer.ts",
    "src/utils/cache.ts",
    "src/models/user.ts",
    "src/models/session.ts",
    "src/core/graph.ts",
    "src/core/parser.ts",
    "src/core/resolver.ts",
    "src/index.ts",
    "src/config.ts",
    "tests/auth.test.ts",
    "tests/db.test.ts",
    "tests/api.test.ts",
    "lib/ast_walker.py",
    "lib/symbol_index.py",
    "lib/dependency_graph.py",
    "lib/cache_layer.py",
    "pipeline/extractor.py",
    "pipeline/ranker.py",
    "pipeline/scorer.py",
    "docs/architecture.md",
    "docs/api_reference.md",
    ".env.example",
    "package.json",
    "tsconfig.json",
    "pyproject.toml",
    "README.md",
    "src/core/knowledge_graph.ts",
    "src/core/node_embeddings.ts",
    "src/core/edge_weights.ts",
    "src/retrieval/bm25.ts",
    "src/retrieval/semantic.ts",
    "src/retrieval/reranker.ts",
    "src/storage/sqlite.ts",
    "src/storage/vector_store.ts",
    "src/hooks/useBeatFrame.ts",
    "src/hooks/useCameraY.ts",
    "src/layouts/TriStat.tsx",
    "src/layouts/StatementSlam.tsx",
    "src/layouts/TakeawayScene.tsx",
    "src/layouts/_shared.tsx",
    "src/CameraViewport.tsx",
    "src/CustomVideo.tsx",
    "src/Root.tsx",
    "src/VideoComposition.tsx",
]

SIZES = [1.2, 2.4, 0.8, 3.1, 1.7, 0.4, 2.9, 1.1, 0.6, 4.2, 1.8, 2.2, 0.9, 1.5, 3.3]


def main():
    sys.stdout.write("\033[2J\033[H")  # clear screen
    sys.stdout.flush()

    # Header
    print(
        f'{BOLD}{GREEN}claude{RESET} {WHITE}"review this codebase — find token inefficiencies"{RESET}\n'
    )
    time.sleep(0.4)

    print(f"{DIM}● Initializing knowledge graph builder...{RESET}")
    time.sleep(0.3)
    print(f"{DIM}● Scanning project structure...{RESET}\n")
    time.sleep(0.3)

    total_tokens = 0
    for i, filepath in enumerate(FILES):
        size = SIZES[i % len(SIZES)]
        tokens = int(size * 1000 + random.randint(-200, 200))
        total_tokens += tokens

        bar_len = min(int(size * 4), 18)
        bar = "█" * bar_len + "░" * (18 - bar_len)

        color = GREEN if size < 2.0 else (CYAN if size < 3.5 else WHITE)
        print(
            f"  {DIM}Reading{RESET}  {color}{filepath:<46}{RESET}  {DIM}{bar}{RESET}  {WHITE}{tokens:>5} tk{RESET}"
        )
        sys.stdout.flush()

        delay = 0.055 + random.uniform(-0.02, 0.04)
        time.sleep(delay)

    print()
    time.sleep(0.3)

    # Summary
    print(f"  {DIM}{'─'*72}{RESET}")
    print(
        f"  {GREEN}✓{RESET}  {WHITE}{len(FILES)} files indexed{RESET}   {DIM}|{RESET}  {WHITE}{total_tokens:,} tokens naïve{RESET}   {DIM}|{RESET}  {CYAN}building AST map...{RESET}"
    )
    sys.stdout.flush()
    time.sleep(0.6)

    print(
        f"  {GREEN}✓{RESET}  {WHITE}Knowledge graph:{RESET} {GREEN}{len(FILES) * 3} nodes, {len(FILES) * 7} edges{RESET}   {DIM}|{RESET}  {CYAN}symbol resolution complete{RESET}"
    )
    sys.stdout.flush()
    time.sleep(0.5)

    compressed = int(total_tokens / 8.2)
    print(
        f"  {GREEN}✓{RESET}  {WHITE}Token footprint:{RESET}  {DIM}{total_tokens:>6,}{RESET}  {GREEN}→  {compressed:>5,} tokens  {BOLD}(8.2x reduction){RESET}"
    )
    sys.stdout.flush()
    time.sleep(1.5)


if __name__ == "__main__":
    main()
