# -*- coding: utf-8 -*-
"""Result-browsing web UI for the eda-gp experiment repository.

Design notes:
- Everything is read live from the filesystem on each request (small TTL
  caches only for expensive log parsing / git invocations, keyed by mtime).
- Markdown + LaTeX are rendered client side (marked.js + KaTeX, vendored).
- The server only serves raw markdown, images, JSON APIs and page shells.
- Binds to 127.0.0.1 only; users reach it through an ssh tunnel.
"""

import csv
import io
import os
import re
import subprocess
import time

from flask import (Flask, abort, jsonify, render_template, request,
                   send_file)

# Repo root = two levels up from tools/webui/
ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
EXP_DIR = os.path.join(ROOT, "experiments")
DOCS_DIR = os.path.join(ROOT, "docs")

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
DIFF_MAX_LINES = 800

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def safe_join_root(relpath):
    """Resolve relpath under ROOT; abort(404) on traversal attempts."""
    if not relpath or relpath.startswith(("/", "\\")):
        abort(404)
    full = os.path.realpath(os.path.join(ROOT, relpath))
    if full != ROOT and not full.startswith(ROOT + os.sep):
        abort(404)
    return full


def read_text(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit) if limit else f.read()
    except OSError:
        return None


def strip_md_inline(s):
    """Remove the most common inline markdown noise for plain-text preview."""
    s = re.sub(r"[*_`]", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s.strip()


# --------------------------------------------------------------------------
# experiment scanning
# --------------------------------------------------------------------------

def readme_summary(readme):
    """Return (title, first paragraph) from a README markdown string."""
    if not readme:
        return None, None
    title = None
    para_lines = []
    in_banner = False
    for line in readme.splitlines():
        stripped = line.strip()
        if title is None:
            if stripped.startswith("#"):
                title = strip_md_inline(stripped.lstrip("#"))
            continue
        # skip blockquote banners (errata etc.) right after the title
        if not para_lines and stripped.startswith(">"):
            in_banner = True
            continue
        if in_banner:
            if stripped == "":
                in_banner = False
            continue
        if stripped == "":
            if para_lines:
                break
            continue
        if stripped.startswith(("#", "|", "```")):
            if para_lines:
                break
            continue
        para_lines.append(stripped)
    para = strip_md_inline(" ".join(para_lines)) if para_lines else None
    if para and len(para) > 220:
        para = para[:220] + "…"
    return title, para


def parse_md_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def find_geomean(exp_dir):
    """Find geomean summary in metrics.md (fallback: README.md).

    Table form: {"header": [...], "row": [...], "source"}; plain-text form
    (e.g. 'geomean wHPWL delta uniform: +2.10%'): {"lines": [...], "source"}.
    """
    for fname in ("metrics.md", "README.md"):
        text = read_text(os.path.join(exp_dir, fname))
        if not text:
            continue
        lines = text.splitlines()
        plain = []
        for i, line in enumerate(lines):
            if "geomean" not in line.lower():
                continue
            if line.strip().startswith("|"):
                # walk back to the table header (row above the |---| rule)
                header = None
                for j in range(i - 1, -1, -1):
                    lj = lines[j].strip()
                    if not lj.startswith("|"):
                        break
                    if re.match(r"^\|[\s:|-]+\|$", lj):
                        if j - 1 >= 0 and lines[j - 1].strip().startswith("|"):
                            header = parse_md_row(lines[j - 1])
                        break
                row = [strip_md_inline(c) for c in parse_md_row(line)]
                if header:
                    header = [strip_md_inline(c) for c in header]
                    n = min(len(header), len(row), 7)
                    return {"header": header[:n], "row": row[:n],
                            "source": fname}
                return {"header": None, "row": row[:7], "source": fname}
            plain.append(strip_md_inline(line))
        if plain:
            return {"lines": plain[:4], "source": fname}
    return None


_order_cache = {"t": 0.0, "data": {}}


def exp_first_commit_ts(name):
    """Unix time of the first commit touching the experiment (cached 5 min);
    None for untracked directories."""
    now = time.time()
    if now - _order_cache["t"] > 300:
        _order_cache["data"] = {}
        _order_cache["t"] = now
    data = _order_cache["data"]
    if name not in data:
        out = run_git(["log", "--reverse", "--format=%at", "--",
                       "experiments/" + name])
        ts = None
        if out:
            lines = out.strip().splitlines()
            if lines:
                try:
                    ts = int(lines[0])
                except ValueError:
                    ts = None
        data[name] = ts
    return data[name]


def list_experiments():
    exps = []
    if not os.path.isdir(EXP_DIR):
        return exps
    for name in os.listdir(EXP_DIR):
        d = os.path.join(EXP_DIR, name)
        if not os.path.isdir(d) or name.startswith("."):
            continue
        readme_path = os.path.join(d, "README.md")
        readme = read_text(readme_path, limit=64 * 1024)
        title, para = readme_summary(readme)
        try:
            mtime = os.path.getmtime(readme_path)
        except OSError:
            mtime = os.path.getmtime(d)
        n_logs = 0
        logs_dir = os.path.join(d, "logs")
        if os.path.isdir(logs_dir):
            for _, _, files in os.walk(logs_dir):
                n_logs += sum(1 for f in files if f.endswith(".log"))
        exps.append({
            "name": name,
            "title": title or name,
            "summary": para,
            "errata": bool(readme and "勘误" in readme),
            "geomean": find_geomean(d),
            "has_metrics": os.path.isfile(os.path.join(d, "metrics.md")),
            "has_csv": os.path.isfile(os.path.join(d, "metrics.csv")),
            "n_logs": n_logs,
            "mtime": mtime,
        })
    # chronological order: first git commit touching the experiment,
    # untracked/new experiments go last (then by name)
    exps.sort(key=lambda e: (exp_first_commit_ts(e["name"]) or 2**62,
                             e["name"]))
    return exps


def exp_dir_or_404(name):
    if not re.match(r"^[\w.-]+$", name):
        abort(404)
    d = os.path.join(EXP_DIR, name)
    if not os.path.isdir(d):
        abort(404)
    return d


# --------------------------------------------------------------------------
# viz scanning
# --------------------------------------------------------------------------

SLICE_RE = re.compile(r"^slice\d+.*\.(png|jpg|jpeg)$", re.I)


def scan_viz(name):
    """Scan experiments/<name>/viz for montages and per-design slices.

    Returns {"groups": [{"name", "montages": [rel...],
                         "designs": [{"name", "slices": [rel...]}]}],
             "curves": [rel...]}
    rel paths are relative to the experiment directory.
    """
    d = os.path.join(EXP_DIR, name)
    viz = os.path.join(d, "viz")
    groups = {}
    if os.path.isdir(viz):
        for dirpath, dirnames, filenames in os.walk(viz):
            dirnames.sort()
            rel_dir = os.path.relpath(dirpath, viz)
            montages = sorted(f for f in filenames if f.endswith("_all.png"))
            slices = sorted(f for f in filenames if SLICE_RE.match(f))
            if montages:
                g = "" if rel_dir == "." else rel_dir
                grp = groups.setdefault(g, {"name": g, "montages": [],
                                            "designs": {}})
                for f in montages:
                    grp["montages"].append(os.path.join("viz", rel_dir, f)
                                           if rel_dir != "." else
                                           os.path.join("viz", f))
            if slices and rel_dir != ".":
                # design dir = last path component; group = its parent
                parent, design = os.path.split(rel_dir)
                g = "" if parent in ("", ".") else parent
                grp = groups.setdefault(g, {"name": g, "montages": [],
                                            "designs": {}})
                grp["designs"][design] = [
                    os.path.join("viz", rel_dir, f) for f in slices]
    out_groups = []
    for g in sorted(groups):
        grp = groups[g]
        out_groups.append({
            "name": g or "（根目录）",
            "montages": grp["montages"],
            "designs": [{"name": k, "slices": v}
                        for k, v in sorted(grp["designs"].items())],
        })
    curves = []
    if os.path.isdir(d):
        curves = sorted(f for f in os.listdir(d)
                        if f.startswith("curves_") and f.endswith(".png"))
    return {"groups": out_groups, "curves": curves}


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

def read_csv_table(path, max_rows=500):
    text = read_text(path)
    if text is None:
        return None
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        return None
    if not rows:
        return None
    return {"header": rows[0], "rows": rows[1:max_rows + 1],
            "truncated": len(rows) - 1 > max_rows}


HEAD_RE = re.compile(r"^(#{1,6})\s*(.+)$")


def readme_results_section(readme):
    """Extract the results-table section of a README (fallback for the A/B
    tab when the experiment has no metrics.md). Returns markdown or None."""
    if not readme:
        return None
    lines = readme.splitlines()
    start = level = None
    for i, line in enumerate(lines):
        m = HEAD_RE.match(line.strip())
        if m and re.search(r"结果|主表|指标|对照|A/B", m.group(2)):
            start, level = i, len(m.group(1))
            break
    if start is None:
        # fallback: first section that contains a table
        for i, line in enumerate(lines):
            m = HEAD_RE.match(line.strip())
            if m:
                for j in range(i + 1, len(lines)):
                    m2 = HEAD_RE.match(lines[j].strip())
                    if m2:
                        break
                    if lines[j].strip().startswith("|"):
                        start, level = i, len(m.group(1))
                        break
            if start is not None:
                break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = HEAD_RE.match(lines[j].strip())
        if m and len(m.group(1)) <= level:
            end = j
            break
    return "\n".join(lines[start:end]).strip()


# --------------------------------------------------------------------------
# log curve parsing (cached by mtime+size)
# --------------------------------------------------------------------------

ITER_RE = re.compile(
    r"iteration\s+(\d+),.*?wHPWL\s+([0-9.Ee+-]+),\s*Overflow\s+([0-9.Ee+-]+)")

_curve_cache = {}  # abspath -> (mtime, size, parsed)


def parse_log_curve(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (st.st_mtime, st.st_size)
    cached = _curve_cache.get(path)
    if cached and cached[0] == key:
        return cached[1]
    iters, whpwl, overflow = [], [], []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = ITER_RE.search(line)
                if m:
                    try:
                        iters.append(int(m.group(1)))
                        whpwl.append(float(m.group(2)))
                        overflow.append(float(m.group(3)))
                    except ValueError:
                        continue
    except OSError:
        return None
    data = None
    if len(iters) >= 2:
        # if the iteration counter restarts (multi-stage runs), fall back to
        # a running index so the x axis stays monotone
        if any(b <= a for a, b in zip(iters, iters[1:])):
            iters = list(range(len(iters)))
        data = {"iter": iters, "whpwl": whpwl, "overflow": overflow}
    _curve_cache[path] = (key, data)
    return data


def collect_curves(name):
    d = os.path.join(EXP_DIR, name, "logs")
    series = []
    if not os.path.isdir(d):
        return series
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames.sort()
        for f in sorted(filenames):
            if not f.endswith(".log"):
                continue
            path = os.path.join(dirpath, f)
            data = parse_log_curve(path)
            if not data:
                continue
            label = os.path.relpath(path, d)[:-len(".log")]
            series.append({"label": label.replace(os.sep, "/"), **data})
    return series


# --------------------------------------------------------------------------
# git (read-only) — commits touching an experiment + core code diffs
# --------------------------------------------------------------------------

def run_git(args, timeout=30):
    try:
        out = subprocess.run(["git", "-C", ROOT] + args, capture_output=True,
                             text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return out.stdout if out.returncode == 0 else None

_git_cache = {}  # name -> (expire_ts, data)


def exp_commits(name):
    now = time.time()
    cached = _git_cache.get(name)
    if cached and cached[0] > now:
        return cached[1]
    commits = []
    log = run_git(["log", "--format=%H%x09%ad%x09%s", "--date=short", "--",
                   "experiments/" + name])
    for line in (log or "").splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        h, date, subject = parts
        stat = run_git(["show", h, "--stat", "--format="]) or ""
        diff = run_git(["show", h, "--format=", "--",
                        "dreamplace-src/dreamplace/*.py", "scripts/*.py"]) or ""
        diff_lines = diff.splitlines()
        truncated = len(diff_lines) > DIFF_MAX_LINES
        if truncated:
            diff = "\n".join(diff_lines[:DIFF_MAX_LINES])
        commits.append({
            "hash": h, "date": date, "subject": subject,
            "stat": stat.strip("\n"),
            "diff": diff,
            "diff_truncated": truncated,
            "diff_total_lines": len(diff_lines),
        })
    _git_cache[name] = (now + 60, commits)
    return commits


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", experiments=list_experiments())


@app.route("/exp/<name>")
def exp_detail(name):
    d = exp_dir_or_404(name)
    viz = scan_viz(name)
    csv_table = read_csv_table(os.path.join(d, "metrics.csv"))
    has_metrics_md = os.path.isfile(os.path.join(d, "metrics.md"))
    extra_md = []  # other renderable tables, e.g. combiner/routing_table.md
    for f in sorted(os.listdir(d)):
        if f.endswith(".md") and f not in ("README.md", "metrics.md"):
            extra_md.append(f)
    results_section = None
    if not has_metrics_md and csv_table is None:
        results_section = readme_results_section(
            read_text(os.path.join(d, "README.md")))
    return render_template(
        "exp.html", name=name, viz=viz, csv_table=csv_table,
        has_metrics_md=has_metrics_md, extra_md=extra_md,
        results_section=results_section,
        errata=bool((read_text(os.path.join(d, "README.md"), 8192) or "")
                    .count("勘误")))


@app.route("/docs")
def docs():
    items = []
    if os.path.isfile(os.path.join(ROOT, "README.md")):
        items.append({"label": "README.md（仓库根）", "rel": "README.md"})
    if os.path.isdir(DOCS_DIR):
        for f in sorted(os.listdir(DOCS_DIR)):
            if f.endswith(".md") and os.path.isfile(os.path.join(DOCS_DIR, f)):
                items.append({"label": f, "rel": "docs/" + f})
    return render_template("docs.html", items=items)


@app.route("/raw")
def raw_markdown():
    rel = request.args.get("p", "")
    if not rel.endswith(".md"):
        abort(404)
    norm = os.path.normpath(rel).replace(os.sep, "/")
    if not (norm == "README.md" or norm.startswith("docs/")
            or norm.startswith("experiments/")):
        abort(404)
    full = safe_join_root(norm)
    if not os.path.isfile(full):
        abort(404)
    text = read_text(full)
    return app.response_class(text, mimetype="text/plain; charset=utf-8")


@app.route("/img/<path:rel>")
def image(rel):
    norm = os.path.normpath(rel).replace(os.sep, "/")
    if not norm.startswith(("experiments/", "docs/", "viz/")):
        abort(404)
    if os.path.splitext(norm)[1].lower() not in IMG_EXTS:
        abort(404)
    full = safe_join_root(norm)
    if not os.path.isfile(full):
        abort(404)
    return send_file(full, conditional=True, max_age=300)


@app.route("/api/exp/<name>/curves")
def api_curves(name):
    exp_dir_or_404(name)
    return jsonify({"series": collect_curves(name)})


@app.route("/api/exp/<name>/commits")
def api_commits(name):
    exp_dir_or_404(name)
    return jsonify({"commits": exp_commits(name)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8377, debug=False, threaded=True)
