"""扫描 app/ 下所有顶层 import，和 requirements.txt 对账。

为什么需要这个：httpx 和 numpy 都是代码里直接 import 的，却只靠 langchain /
chromadb 传递进来。传递依赖随时可能因为上游改版而消失，那时就是 ImportError。
反过来，声明了却没用的包会让安装变慢、攻击面变大。

用法：python scripts/check_requirements.py
退出码 1 表示有不一致（可以用在 CI 里）。
"""
import ast
import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(BACKEND_DIR, "app")
REQUIREMENTS = os.path.join(BACKEND_DIR, "requirements.txt")

# import 名 -> PyPI 分发名（不一致的才需要列在这里）
IMPORT_TO_DIST = {
    "jose": "python-jose",
    "pydantic_settings": "pydantic-settings",
    "rank_bm25": "rank-bm25",
    "langchain_core": "langchain-core",
    "langchain_community": "langchain-community",
    "langchain_chroma": "langchain-chroma",
    "langchain_text_splitters": "langchain-text-splitters",
    "langchain_openai": "langchain-openai",
    "multipart": "python-multipart",
    "dotenv": "python-dotenv",
}

# 标准库和本项目自己的包，不需要声明
SKIP = {"app", "tests", "scripts"}

# 这些不会出现在 import 语句里，但确实需要 —— 写清楚理由，
# 免得后来者（或者未来的我）看到「已声明但没用到」就顺手删掉。
INDIRECT_OK = {
    "pypdf": "langchain_community 的 PyPDFLoader 运行时需要它来解析 PDF",
    "python-multipart": "FastAPI 解析 multipart/form-data（文件上传）需要它",
    "uvicorn": "进程入口是 `uvicorn` 命令，不是 import",
    "bcrypt": "passlib 的哈希后端，且这里显式限制在 4.x（passlib 1.7.4 与 5.x 不兼容）",
    "langchain": "langchain-community 依赖的生态总包",
}

# 这些是运行时本来就有的（标准库），不用声明
import sys as _sys

STDLIB = set(_sys.stdlib_module_names) | {"__future__"}


def collect_imports() -> set[str]:
    found: set[str] = set()
    for root, _dirs, files in os.walk(APP_DIR):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        found.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        found.add(node.module.split(".")[0])
    return found


def declared_requirements() -> set[str]:
    declared = set()
    with open(REQUIREMENTS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # 去掉版本约束和 extras：foo[bar]>=1.0 -> foo
            name = re.split(r"[<>=!\[;]", line)[0].strip().lower()
            if name:
                declared.add(name)
    return declared


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    imports = collect_imports() - STDLIB - SKIP
    as_dists = {IMPORT_TO_DIST.get(m, m).lower() for m in imports}
    declared = declared_requirements()

    missing = sorted(as_dists - declared)
    unused = sorted(declared - as_dists - set(INDIRECT_OK))

    print(f"代码里直接 import 的第三方包: {len(as_dists)} 个")
    print(f"requirements.txt 声明的包:    {len(declared)} 个\n")

    if missing:
        print("【未声明】代码直接 import，但 requirements.txt 里没有：")
        for m in missing:
            print(f"  - {m}")
        print("  这类是传递依赖，上游一变就会 ImportError。\n")
    else:
        print("【未声明】无\n")

    if unused:
        print("【已声明但代码里没 import】")
        for u in unused:
            print(f"  - {u}")
        print("  要么删掉，要么在脚本的 INDIRECT_OK 里写上保留理由。\n")
    else:
        print("【已声明但代码里没 import】无\n")

    # 只把「未声明」当错误：漏声明会导致装不上/装错，
    # 「声明了但没直接用」有可能是合理的（运行时工具、间接必需）。
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
