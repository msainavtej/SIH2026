import ast
import os
import sys
from pathlib import Path

ROOT = Path("C:/Users/HEMANTH/Desktop/SKYNET")
SKIP_DIRS = {".venv", ".git", "node_modules", ".agents", "__pycache__", ".pytest_cache"}

print("=" * 70)
print("AST-BASED IMPORT & FUNCTION CALL FORENSIC AUDIT")
print("=" * 70)

prohibited_modules = [
    "torchreid",
    "osnet",
    "botsort",
    "networkx",
    "scipy.optimize",
]

prohibited_calls = [
    "linear_sum_assignment",
    "extract_features",
    "extract_embedding",
    "get_embedding",
    "cosine_similarity",
]

findings = []

for py_file in ROOT.rglob("*.py"):
    if any(skip in py_file.parts for skip in SKIP_DIRS):
        continue
    rel_path = py_file.relative_to(ROOT)
    
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception as e:
        print(f"Error parsing {rel_path}: {e}")
        continue
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for pm in prohibited_modules:
                    if pm in alias.name:
                        findings.append((str(rel_path), node.lineno, f"Prohibited module import: {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for pm in prohibited_modules:
                if pm in mod:
                    findings.append((str(rel_path), node.lineno, f"Prohibited module from-import: {mod}"))
            for alias in node.names:
                if alias.name in prohibited_calls:
                    findings.append((str(rel_path), node.lineno, f"Prohibited symbol import: {alias.name} from {mod}"))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in prohibited_calls:
                    findings.append((str(rel_path), node.lineno, f"Prohibited function call: {node.func.id}()"))
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in prohibited_calls:
                    findings.append((str(rel_path), node.lineno, f"Prohibited method call: .{node.func.attr}()"))

print(f"AST Analysis scanned all Python source files.")
if findings:
    print(f"FAILED: Found {len(findings)} prohibited AST entries:")
    for file, line, desc in findings:
        print(f"  {file}:{line} -> {desc}")
else:
    print("PASSED: 0 prohibited AST imports or calls found across entire codebase!")

print("\n" + "=" * 70)
print("IDENTITY OVERCLAIMING STRING AUDIT (LOGS, STRINGS, UI)")
print("=" * 70)

# Check all string literals in AST for overclaiming
overclaim_findings = []
target_dirs = ["intelligence", "backend", "ai", "simulator"]
for td in target_dirs:
    dir_path = ROOT / td
    for py_file in dir_path.rglob("*.py"):
        if any(skip in py_file.parts for skip in SKIP_DIRS):
            continue
        rel_path = py_file.relative_to(ROOT)
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value.lower()
                for target_phrase in ["same person", "confirmed identity", "confirmed person", "identity match", "matched identity", "re-identified person"]:
                    # exclude test assertions or negative verification checks
                    if target_phrase in s:
                        overclaim_findings.append((str(rel_path), node.lineno, node.value))

print(f"Found {len(overclaim_findings)} string literal occurrences:")
for f, l, val in overclaim_findings:
    print(f"  {f}:{l} -> \"{val}\"")
