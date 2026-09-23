"""Хранение заметок: загрузка/сохранение JSON в ~/.local/share/tacklet/notes.json."""

import json
import os
import uuid
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path

from .util import clamp

MIN_W, MIN_H = 180, 140
DEFAULT_COLOR = '#fdf6d8'
DEFAULT_OPACITY = 0.85
DEFAULT_FONT = 14
TRASH_RETENTION_DAYS = 30
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
    # Дополнительные секции одной заметки: code и checklist.
    blocks: list = field(default_factory=list)

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
            blocks=data.get('blocks', []),
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
            'blocks': self.blocks,
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
        self.blocks = normalize_blocks(self.blocks)


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


def _utc_now():
    return datetime.now(timezone.utc)


@dataclass
class TrashEntry:
    """A deleted note retained locally for a limited recovery period."""

    note: NoteData
    deleted_at: str = field(default_factory=lambda: _utc_now().isoformat())

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not isinstance(data.get('note'), dict):
            return None
        timestamp = _parse_timestamp(data.get('deleted_at'))
        if timestamp is None:
            return None
        return cls(note=NoteData.from_dict(data['note']),
                   deleted_at=timestamp.isoformat())

    def to_dict(self):
        return {'note': self.note.to_dict(), 'deleted_at': self.deleted_at}

    def is_expired(self, now=None):
        timestamp = _parse_timestamp(self.deleted_at)
        if timestamp is None:
            return True
        return timestamp + timedelta(days=TRASH_RETENTION_DAYS) <= (now or _utc_now())


@dataclass
class AppState:
    config: AppConfig = field(default_factory=AppConfig)
    notes: list = field(default_factory=list)
    trash: list = field(default_factory=list)


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
    raw_trash = raw.get('trash', [])
    if not isinstance(raw_trash, list):
        raw_trash = []
    trash = [entry for entry in (TrashEntry.from_dict(item)
             for item in raw_trash) if entry]
    return AppState(config=config, notes=notes, trash=prune_trash(trash))


def save(state):
    """Атомарно сохраняет состояние (пишет во временный файл, затем переименовывает)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state.trash[:] = prune_trash(state.trash)
    _write_payload(NOTES_FILE, _payload(state))


def export_file(destination, state):
    """Write a portable Tacklet backup selected by the user."""
    _write_payload(Path(destination), _payload(state))


def _payload(state):
    return {
        'version': 2,
        'config': {
            'opacity': state.config.opacity,
            'font_size': state.config.font_size,
            'color': state.config.color,
            'hotkey_enabled': state.config.hotkey_enabled,
        },
        'notes': [n.to_dict() for n in state.notes],
        'trash': [entry.to_dict() for entry in prune_trash(state.trash)],
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


def _parse_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            return None
        return timestamp.astimezone(timezone.utc)
    except ValueError:
        return None


def prune_trash(entries, now=None):
    """Drop malformed and expired entries before they reach persistent data."""
    current_time = now or _utc_now()
    return [entry for entry in entries
            if isinstance(entry, TrashEntry) and not entry.is_expired(current_time)]


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


def new_block(kind, text=''):
    """Create a block in the portable JSON shape used by one note."""
    block = {'id': uuid.uuid4().hex[:8], 'kind': kind}
    if kind == 'code':
        block['text'] = text
    elif kind == 'checklist':
        block['items'] = [new_checklist_item(text)]
    return block


def new_checklist_item(text=''):
    return {'id': uuid.uuid4().hex[:8], 'text': text, 'checked': False}


def normalize_blocks(blocks):
    """Keep only safe, forward-compatible code and checklist blocks."""
    if not isinstance(blocks, list):
        return []
    result = []
    seen_ids = set()
    for raw in blocks:
        if not isinstance(raw, dict) or raw.get('kind') not in ('code', 'checklist'):
            continue
        block_id = str(raw.get('id') or uuid.uuid4().hex[:8])
        while block_id in seen_ids:
            block_id = uuid.uuid4().hex[:8]
        seen_ids.add(block_id)
        if raw['kind'] == 'code':
            result.append({'id': block_id, 'kind': 'code',
                           'text': str(raw.get('text') or '')})
            continue
        items = []
        seen_item_ids = set()
        raw_items = raw.get('items', [])
        if isinstance(raw_items, list):
            for raw_item in raw_items:
                if not isinstance(raw_item, dict):
                    continue
                item_id = str(raw_item.get('id') or uuid.uuid4().hex[:8])
                while item_id in seen_item_ids:
                    item_id = uuid.uuid4().hex[:8]
                seen_item_ids.add(item_id)
                items.append({
                    'id': item_id,
                    'text': str(raw_item.get('text') or ''),
                    'checked': raw_item.get('checked') is True,
                })
        result.append({'id': block_id, 'kind': 'checklist', 'items': items})
    return result
