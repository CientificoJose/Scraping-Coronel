"""
Script generador del Grafo de Conocimiento del repositorio Scraping-Coronel.
Analiza el AST (Abstract Syntax Tree) de todos los módulos Python del proyecto
para mapear funciones, clases, imports, tablas de SQLite y llamadas a APIs externas.

Genera:
- docs/code_graph.json (para indexación RAG / LLM / Grafos)
- docs/KNOWLEDGE_GRAPH.md (para visualización y lectura directa con bajo consumo de tokens)
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Set

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "api_cache",
    "img-scraping",
    "productos_coronel",
    "openai_logs",
    "scratch",
}

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"


class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath: Path, root_path: Path):
        self.filepath = filepath
        self.rel_path = filepath.relative_to(root_path).as_posix()
        self.imports: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.calls: Set[str] = set()
        self.sql_tables: Set[str] = set()
        self.external_apis: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append({"module": alias.name, "alias": alias.asname})
            self._check_external_api(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append({"from": mod, "name": alias.name, "alias": alias.asname})
            self._check_external_api(mod)
        self.generic_visit(node)

    def _check_external_api(self, module_name: str):
        if "openai" in module_name.lower():
            self.external_apis.add("OpenAI API")
        elif "selenium" in module_name.lower():
            self.external_apis.add("Selenium (Coronel Mayorista)")
        elif "tiendanube" in module_name.lower():
            self.external_apis.add("Tiendanube REST API")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = [arg.arg for arg in node.args.args]
        docstring = ast.get_docstring(node) or ""
        first_line = docstring.strip().split("\n")[0] if docstring else ""
        self.functions.append({
            "name": node.name,
            "args": args,
            "line": node.lineno,
            "docstring": first_line,
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        args = [arg.arg for arg in node.args.args]
        docstring = ast.get_docstring(node) or ""
        first_line = docstring.strip().split("\n")[0] if docstring else ""
        self.functions.append({
            "name": node.name,
            "args": args,
            "is_async": True,
            "line": node.lineno,
            "docstring": first_line,
        })
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        docstring = ast.get_docstring(node) or ""
        first_line = docstring.strip().split("\n")[0] if docstring else ""
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "methods": methods,
            "docstring": first_line,
        })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            val_upper = node.value.upper()
            if "FROM " in val_upper or "INTO " in val_upper or "TABLE " in val_upper:
                # Detección básica de tablas SQL
                matches = re.findall(r"(?:FROM|INTO|UPDATE|TABLE\s+IF\s+NOT\s+EXISTS|TABLE)\s+([a-zA-Z_0-9]+)", val_upper)
                for m in matches:
                    if m not in {"SELECT", "SET", "WHERE"}:
                        self.sql_tables.add(m.lower())
        self.generic_visit(node)


def scan_codebase(root_path: Path) -> Dict[str, Any]:
    nodes = {}
    edges = []

    for current_root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if not file.endswith(".py"):
                continue

            filepath = Path(current_root) / file
            rel_path = filepath.relative_to(root_path).as_posix()

            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                tree = ast.parse(content, filename=filepath.name)
            except Exception as e:
                print(f"Error analizando {rel_path}: {e}")
                continue

            analyzer = CodeAnalyzer(filepath, root_path)
            analyzer.visit(tree)

            loc = len(content.splitlines())
            nodes[rel_path] = {
                "file": rel_path,
                "lines_of_code": loc,
                "imports": analyzer.imports,
                "functions": analyzer.functions,
                "classes": analyzer.classes,
                "sql_tables": sorted(list(analyzer.sql_tables)),
                "external_apis": sorted(list(analyzer.external_apis)),
            }

            # Construir dependencias internas (edges)
            for imp in analyzer.imports:
                mod = imp.get("module") or imp.get("from") or ""
                # Si importa algo de app o módulos locales
                target_file = None
                if mod.startswith("app."):
                    potential = mod.replace(".", "/") + ".py"
                    if (root_path / potential).exists():
                        target_file = potential
                elif (root_path / f"{mod}.py").exists():
                    target_file = f"{mod}.py"

                if target_file and target_file != rel_path:
                    edges.append({
                        "source": rel_path,
                        "target": target_file,
                        "relation": "imports",
                        "imported_name": imp.get("name") or imp.get("module"),
                    })

    # Deduplicar edges
    unique_edges = []
    seen_edges = set()
    for e in edges:
        key = (e["source"], e["target"], e["imported_name"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    return {
        "metadata": {
            "project_name": "Scraping-Coronel",
            "total_modules": len(nodes),
            "generated_by": "tools/generate_code_graph.py",
        },
        "nodes": nodes,
        "edges": unique_edges,
    }


def generate_markdown_report(graph_data: Dict[str, Any], output_md: Path):
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    md_lines = [
        "# 🌐 Grafo de Conocimiento del Código (Knowledge Graph)",
        "",
        "> Este documento describe la estructura modular, relaciones, llamadas y puntos de entrada",
        "> del repositorio para que cualquier agente de IA o desarrollador pueda navegarlo con mínimo consumo de tokens.",
        "",
        "## 📊 Resumen General",
        f"- **Módulos Python analizados:** {len(nodes)}",
        f"- **Relaciones internas detectadas:** {len(edges)}",
        "",
        "## 🗺️ Mapa de Relaciones (Mermaid Graph)",
        "```mermaid",
        "graph TD",
    ]

    # Subgrafos mermaid
    app_core = []
    app_services = []
    root_scripts = []

    for file_path in nodes.keys():
        safe_id = file_path.replace("/", "_").replace(".", "_").replace("-", "_")
        if file_path.startswith("app/core/"):
            app_core.append((safe_id, file_path))
        elif file_path.startswith("app/services/"):
            app_services.append((safe_id, file_path))
        else:
            root_scripts.append((safe_id, file_path))

    md_lines.append("    subgraph Core [Capa Core]")
    for safe_id, file_path in app_core:
        md_lines.append(f'        {safe_id}["{file_path}"]')
    md_lines.append("    end")

    md_lines.append("    subgraph Services [Capa Servicios]")
    for safe_id, file_path in app_services:
        md_lines.append(f'        {safe_id}["{file_path}"]')
    md_lines.append("    end")

    md_lines.append("    subgraph Scripts [Scripts & CLI]")
    for safe_id, file_path in root_scripts:
        md_lines.append(f'        {safe_id}["{file_path}"]')
    md_lines.append("    end")

    # Edges en mermaid
    for e in edges:
        s = e["source"].replace("/", "_").replace(".", "_").replace("-", "_")
        t = e["target"].replace("/", "_").replace(".", "_").replace("-", "_")
        md_lines.append(f"    {s} -->|importa| {t}")

    md_lines.append("```")
    md_lines.append("")
    md_lines.append("## 📦 Diccionario de Módulos y Símbolos")
    md_lines.append("")

    for rel_path, data in sorted(nodes.items()):
        md_lines.append(f"### 📄 [`{rel_path}`](file:///{ROOT_DIR.as_posix()}/{rel_path}) ({data['lines_of_code']} líneas)")
        
        if data["external_apis"]:
            md_lines.append(f"- **APIs / Conexiones Externas:** {', '.join(data['external_apis'])}")
        if data["sql_tables"]:
            md_lines.append(f"- **Tablas SQLite usadas:** {', '.join(data['sql_tables'])}")

        if data["classes"]:
            md_lines.append("- **Clases:**")
            for c in data["classes"]:
                doc = f" - _{c['docstring']}_" if c['docstring'] else ""
                md_lines.append(f"  - `class {c['name']}` (Línea {c['line']}){doc}")
                if c["methods"]:
                    md_lines.append(f"    - Métodos: `{', '.join(c['methods'])}`")

        if data["functions"]:
            md_lines.append("- **Funciones principales:**")
            for f in data["functions"]:
                async_prefix = "async " if f.get("is_async") else ""
                args_str = ", ".join(f["args"])
                doc = f" - _{f['docstring']}_" if f['docstring'] else ""
                md_lines.append(f"  - `{async_prefix}{f['name']}({args_str})` (Línea {f['line']}){doc}")

        md_lines.append("")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    graph_data = scan_codebase(ROOT_DIR)

    json_path = DOCS_DIR / "code_graph.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Grafo en formato JSON generado: {json_path}")

    md_path = DOCS_DIR / "KNOWLEDGE_GRAPH.md"
    generate_markdown_report(graph_data, md_path)
    print(f"✅ Documento Markdown del grafo generado: {md_path}")


if __name__ == "__main__":
    main()
