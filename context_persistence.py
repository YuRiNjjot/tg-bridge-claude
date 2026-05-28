"""Персистентный контекст для Claude Code сессий.

Логика:
- При ЗАГРУЗКЕ: мержим данные из корневой папки + mempalace + локальной папки.
  Приоритет: локальные заметки перекрывают корневые, корневые — mempalace.
- При СОХРАНЕНИИ: пишем в локальную папку + реплицируем в корневую.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent if (BASE_DIR.parent / ".claude").exists() else BASE_DIR
MEMPALACE_DIR = ROOT_DIR / "mempalace"


def _path_local() -> Path:
    return Path(os.getcwd()) / ".claude" / "context.json"


def _path_root() -> Path:
    return ROOT_DIR / ".claude" / "context.json"


def _path_mempalace() -> Optional[Path]:
    return MEMPALACE_DIR / "context.json" if MEMPALACE_DIR.exists() else None


def _load_raw(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.pop("_source", None)
            data.pop("_updated_at", None)
            return data
    except Exception as e:
        print(f"[Context] Load error {path}: {e}")
        return None


def _merge_field(dst: List, src: List) -> List:
    """Объединить списки по timestamp, избегая дублей."""
    seen = {json.dumps(x, sort_keys=True) for x in dst}
    for item in src:
        key = json.dumps(item, sort_keys=True)
        if key not in seen:
            dst.append(item)
    return sorted(dst, key=lambda x: x.get("timestamp", ""))


def load_context() -> Dict:
    """Загружает и мержит контекст из всех источников.
    Приоритет: local > root > mempalace.
    """
    sources = [
        ("mempalace", _path_mempalace()),
        ("root", _path_root()),
        ("local", _path_local()),
    ]

    merged = {
        "sessions": [],
        "notes": [],
        "commands_history": [],
        "created_at": datetime.now().isoformat(),
    }

    loaded_from = []
    for name, path in sources:
        if path is None:
            continue
        raw = _load_raw(path)
        if raw:
            loaded_from.append(name)
            merged["sessions"] = _merge_field(merged["sessions"], raw.get("sessions", []))
            merged["notes"] = _merge_field(merged["notes"], raw.get("notes", []))
            merged["commands_history"] = _merge_field(
                merged["commands_history"], raw.get("commands_history", [])
            )
            if raw.get("created_at") and raw["created_at"] < merged["created_at"]:
                merged["created_at"] = raw["created_at"]

    merged["_sources"] = loaded_from
    return merged


def save_context(context: Dict, target_dir: Optional[Path] = None):
    """Сохраняет контекст в локальную папку и реплицирует в корневую."""
    # Удаляем служебные поля перед записью
    clean = {k: v for k, v in context.items() if not k.startswith("_")}
    clean["_updated_at"] = datetime.now().isoformat()

    dirs = []
    # Локальная папка
    if target_dir:
        dirs.append(target_dir / ".claude")
    else:
        dirs.append(Path(os.getcwd()) / ".claude")

    # Корневая — всегда реплицируем
    root_claude = _path_root().parent
    if root_claude not in dirs:
        dirs.append(root_claude)

    for d in dirs:
        d.mkdir(exist_ok=True)
        path = d / "context.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)
        print(f"[Context] Saved to {path}")


def append_session_note(note: str, target_dir: Optional[Path] = None):
    ctx = load_context()
    ctx.setdefault("notes", []).append({
        "timestamp": datetime.now().isoformat(),
        "note": note,
    })
    save_context(ctx, target_dir)


def add_command_to_history(command: str, description: str = "", target_dir: Optional[Path] = None):
    ctx = load_context()
    ctx.setdefault("commands_history", []).append({
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "description": description,
    })
    ctx["commands_history"] = ctx["commands_history"][-100:]
    save_context(ctx, target_dir)


def get_recent_notes(n: int = 10) -> List[str]:
    ctx = load_context()
    notes = ctx.get("notes", [])
    return [f"{n['timestamp']}: {n['note']}" for n in notes[-n:]]


def get_context_summary() -> str:
    """Возвращает краткое резюме для вставки в промпт агента."""
    ctx = load_context()
    notes = ctx.get("notes", [])
    sessions = ctx.get("sessions", [])
    history = ctx.get("commands_history", [])
    sources = ctx.get("_sources", [])

    lines = ["=== КОНТЕКСТ ПРОЕКТА ==="]

    if sessions:
        lines.append(f"Сессий: {len(sessions)}")
        last = sessions[-1]
        lines.append(f"Последняя: {last.get('started_at', 'unknown')[:10]}")

    if notes:
        lines.append(f"Заметок: {len(notes)}")
        for n in notes[-5:]:
            lines.append(f"  - [{n['timestamp'][:10]}] {n['note'][:80]}")

    if history:
        lines.append(f"Команд: {len(history)}")
        for h in history[-3:]:
            lines.append(f"  - {h['command'][:60]}")

    lines.append(f"Источники: {', '.join(sources) if sources else 'новый'}")
    lines.append("=== /КОНТЕКСТ ===")
    return "\n".join(lines)
