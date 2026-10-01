"""从 requirements.txt 生成 requirements.lock（固定到精确版本）。

用 pip 自己的解析器来算依赖图（install --dry-run --report），所以结果和真正
安装时一致；但**不装任何东西**，只让 pip 把图算出来。

为什么需要锁文件：requirements.txt 里写的是版本区间（>=），半年后重新
pip install 会装上一批更新的包 —— 上游任何一个不兼容的改动都会让项目在你
本机跑得好好的、换台机器就起不来。

用法：
    python scripts/gen_lock.py
"""
import json
import os
import subprocess
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(BACKEND_DIR, "requirements.txt")
LOCK = os.path.join(BACKEND_DIR, "requirements.lock")

HEADER = """\
# 自动生成，请勿手改 —— 改 requirements.txt 后重新跑：
#     python scripts/gen_lock.py
#
# 这是 requirements.txt 的**精确版本**解析结果，用于可复现安装：
#     pip install -r requirements.lock
#
# 生成方式：pip install --dry-run --report（用 pip 自己的解析器算依赖图，
# 不实际安装）。因此这里的版本就是当时 pip 会装的那一套。
#
# 没有带哈希（--require-hashes）。版本锁定已经挡住绝大多数「换台机器就崩」，
# 哈希防的是包被投毒；需要的话再单独加。
#
# 生成环境：
#     Python {py_version}
#     pip {pip_version}
#
# 包总数：{count}
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        report_path = f.name

    try:
        print("正在用 pip 解析依赖图（不安装任何东西）...")
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--dry-run", "--quiet",
                "--ignore-installed",       # 不受当前 venv 里已装包的影响
                "--report", report_path,
                "-r", REQUIREMENTS,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            print("pip 解析失败：", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return 1

        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)

        pins = {
            item["metadata"]["name"]: item["metadata"]["version"]
            for item in report.get("install", [])
        }
        # 按包名小写排序，跟 pip freeze 的习惯一致
        ordered = sorted(pins.items(), key=lambda kv: kv[0].lower())

        # 在进程内取 pip 版本，不再开子进程 —— 子进程的 stdout.readline
        # 会用系统 locale（中文 Windows 是 GBK）解码，pip 输出里的非 ASCII
        # 字节会直接 UnicodeDecodeError。
        try:
            import pip  # noqa: PLC0415

            pip_version = pip.__version__
        except Exception:
            pip_version = "unknown"

        with open(LOCK, "w", encoding="utf-8", newline="\n") as f:
            f.write(HEADER.format(
                py_version=".".join(map(str, sys.version_info[:3])),
                pip_version=pip_version,
                count=len(ordered),
            ))
            for name, version in ordered:
                f.write(f"{name}=={version}\n")

        print(f"已写入 {LOCK}")
        print(f"共 {len(ordered)} 个包")
        return 0
    finally:
        if os.path.exists(report_path):
            os.remove(report_path)


if __name__ == "__main__":
    sys.exit(main())
