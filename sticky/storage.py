"""Хранение заметок: загрузка/сохранение JSON в ~/.local/share/tacklet/notes.json."""

import json
import os
import uuid
import re
from dataclasses import dataclass, field
from pathlib import Path

from .util import clamp

MIN_W, MIN_H = 180, 140
DEFAULT_COLOR = '#fdf6d8'
DEFAULT_OPACITY = 0.85
DEFAULT_FONT = 14
HEX_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')

HOME = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
DATA_DIR = HOME / 'tacklet'
NOTES_FILE = DATA_DIR / 'notes.json'
LEGACY_NOTES_FILE = HOME / 'sticky-notes' / 'notes.json'


@dataclass
class NoteData:
    """Одна заметка. Поля сохраняются в JSON."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ''
    text: str = ''
    x: int = 90
    y: int = 90
    w: int = 280
    h: int = 240
    color: str = DEFAULT_COLOR
    font_size: int = DEFAULT_FONT
    opacity: float = DEFAULT_OPACITY
    hidden: bool = False
    # Локальные интервалы размера шрифта: [{start, end, font_size}].
    formats: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        note = cls(
            id=str(data.get('id') or uuid.uuid4().hex[:8]),
            title=str(data.get('title') or ''),
            text=str(data.get('text') or ''),
            x=_as_int(data.get('x'), 90),
            y=_as_int(data.get('y'), 90),
            w=_as_int(data.get('w'), 280),
            h=_as_int(data.get('h'), 240),
            color=str(data.get('color', DEFAULT_COLOR)),
            font_size=_as_int(data.get('font_size'), DEFAULT_FONT),
            opacity=_as_float(data.get('opacity'), DEFAULT_OPACITY),
            hidden=bool(data.get('hidden', False)),
            formats=data.get('formats', []),
        )
        note.normalize()
        return note

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'text': self.text,
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
            'color': self.color,
            'font_size': self.font_size,
            'opacity': self.opacity,
            'hidden': self.hidden,
            'formats': self.formats,
        }

    def normalize(self):
        self.title = self.title.strip()[:120]
        self.w = clamp(int(self.w), MIN_W, 4000)
        self.h = clamp(int(self.h), MIN_H, 4000)
        self.opacity = clamp(float(self.opacity), 0.05, 1.0)
        self.font_size = clamp(int(self.font_size), 8, 48)
        if not HEX_COLOR.fullmatch(self.color):
            self.color = DEFAULT_COLOR
        self.formats = _normalize_formats(self.formats, len(self.text))


@dataclass
class AppConfig:
    """Общие настройки (используются для новых заметок и глобально)."""

    opacity: float = DEFAULT_OPACITY
    font_size: int = DEFAULT_FONT
    color: str = DEFAULT_COLOR
    hotkey_enabled: bool = True

    @classmethod
    def from_dict(cls, data):
        cfg = data if isinstance(data, dict) else {}
        config = cls(
            opacity=clamp(_as_float(cfg.get('opacity'), DEFAULT_OPACITY), 0.05, 1.0),
            font_size=clamp(_as_int(cfg.get('font_size'), DEFAULT_FONT), 8, 48),
            color=str(cfg.get('color', DEFAULT_COLOR)),
            hotkey_enabled=cfg.get('hotkey_enabled', True) is True,
        )
        if not HEX_COLOR.fullmatch(config.color):
            config.color = DEFAULT_COLOR
        return config


@dataclass
class AppState:
    config: AppConfig = field(default_factory=AppConfig)
    notes: list = field(default_factory=list)


def load():
    """Читает состояние из файла. При любой ошибке возвращает пустое состояние."""
    source = NOTES_FILE if NOTES_FILE.exists() else LEGACY_NOTES_FILE
    try:
        return load_file(source)
    except ValueError:
        return AppState()

def load_file(source):
    """Read a Tacklet export and return normalized state or raise ValueError."""
    try:
        raw = json.loads(Path(source).read_text(encoding='utf-8'))
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise ValueError('Файл не является корректным экспортом Tacklet.') from exc
    if not isinstance(raw, dict):
        raise ValueError('Файл не является корректным экспортом Tacklet.')
    config = AppConfig.from_dict(raw.get('config'))
    raw_notes = raw.get('notes', [])
    if not isinstance(raw_notes, list):
        raise ValueError('В экспорте Tacklet отсутствует список заметок.')
    notes = [NoteData.from_dict(d) for d in raw_notes if isinstance(d, dict)]
    return AppState(config=config, notes=notes)


def save(state):
    """Атомарно сохраняет состояние (пишет во временный файл, затем переименовывает)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_payload(NOTES_FILE, _payload(state))


def export_file(destination, state):
    """Write a portable Tacklet backup selected by the user."""
    _write_payload(Path(destination), _payload(state))


def _payload(state):
    return {
        'version': 1,
        'config': {
            'opacity': state.config.opacity,
            'font_size': state.config.font_size,
            'color': state.config.color,
            'hotkey_enabled': state.config.hotkey_enabled,
        },
        'notes': [n.to_dict() for n in state.notes],
    }


def _write_payload(destination, payload):
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f'.{destination.name}.tmp')
    # Не оставляем читаемый всем пользователям временный файл и подтверждаем
    # запись на диск до атомарного rename: заметки переживают внезапный выход.
    with open(tmp, 'w', encoding='utf-8') as handle:
        os.fchmod(handle.fileno(), 0o600)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, destination)


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_formats(formats, text_length):
    """Оставляет только безопасные интервалы размера шрифта."""
    if not isinstance(formats, list):
        return []
    result = []
    for item in formats:
        if not isinstance(item, dict):
            continue
        start = clamp(_as_int(item.get('start'), 0), 0, text_length)
        end = clamp(_as_int(item.get('end'), 0), 0, text_length)
        size = clamp(_as_int(item.get('font_size'), DEFAULT_FONT), 6, 72)
        if end > start:
            result.append({'start': start, 'end': end, 'font_size': size})
    return result
