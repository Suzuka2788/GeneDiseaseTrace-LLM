"""Write the parsed paper as work/blocks.txt (for reading) and work/source_blocks.json.

Usage: python -m toolkit.blocks
"""
import json
from pathlib import Path

from .common import load_article, sha256


def main():
    path, article, _ = load_article()
    work = Path("work")
    work.mkdir(exist_ok=True)
    lines = [f"# {article['paper_id']} | {article['article_type']} | {article['title']}",
             f"# source_sha256 {sha256(path)} | {len(article['blocks'])} blocks | warnings: {'; '.join(article['warnings'])}", ""]
    for b in article["blocks"]:
        lines.append(f"[{b['block_id']} | {b['content_type']} | {b['section']}]")
        lines.append(b["text"])
        lines.append("")
    (work / "blocks.txt").write_text("\n".join(lines), encoding="utf-8")
    (work / "source_blocks.json").write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"work/blocks.txt: {len(article['blocks'])} blocks, {sum(len(b['text']) for b in article['blocks'])} characters")


if __name__ == "__main__":
    main()
