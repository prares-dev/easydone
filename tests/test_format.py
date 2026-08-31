import builtins
import importlib
import sys
import types


def _reload_format_module(monkeypatch, *, rich_available):
    """Import reload helper to simulate rich availability or absence."""
    if rich_available:
        rich_mod = types.ModuleType("rich")
        console_mod = types.ModuleType("rich.console")
        table_mod = types.ModuleType("rich.table")
        text_mod = types.ModuleType("rich.text")

        class FakeConsole:
            instances = []

            def __init__(self):
                self.rendered = []
                FakeConsole.instances.append(self)

            def print(self, table):
                self.rendered.append(table)

        class FakeTable:
            def __init__(self, show_header=True, header_style=None):
                self.show_header = show_header
                self.header_style = header_style
                self.columns = []
                self.rows = []

            def add_column(self, *args, **kwargs):
                self.columns.append(args[0])

            def add_row(self, *row):
                self.rows.append(row)

        class FakeText:
            def __init__(self, text, overflow=None, style=None):
                self.text = text
                self.overflow = overflow
                self.style = style

            def __str__(self):
                return self.text

        console_mod.Console = FakeConsole   # type: ignore
        table_mod.Table = FakeTable # type: ignore
        text_mod.Text = FakeText    # type: ignore

        monkeypatch.setitem(sys.modules, "rich", rich_mod)
        monkeypatch.setitem(sys.modules, "rich.console", console_mod)
        monkeypatch.setitem(sys.modules, "rich.table", table_mod)
        monkeypatch.setitem(sys.modules, "rich.text", text_mod)
    else:
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("rich"):
                raise ImportError("simulated missing rich")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

    sys.modules.pop("easydone.format", None)
    return importlib.import_module("easydone.format")


def test_print_table_uses_plain_text_fallback(monkeypatch, capsys):
    """When Rich is missing, output should still be readable plain text."""
    format_module = _reload_format_module(monkeypatch, rich_available=False)

    tasks = {
        "123": {
            "description": "read a book",
            "status": "not-done",
            "priority": "low",
            "created-at": "2026-08-22",
            "updated-at": None,
        }
    }

    format_module.print_table(tasks, ["123"])

    output = capsys.readouterr().out
    assert "easydone: task tracker" in output
    assert all(str in output for str in['ID: 123', "read a book", "low" ,"not-done", "2026-08-22", "-"])
    
    format_module.print_table(tasks, ["123"], no_dates=True)
    
    output = capsys.readouterr().out
    assert "easydone: task tracker" in output
    assert all(str in output for str in ['ID: 123', "read a book", "low" ,"not-done"])
    assert not "2026-08-22" in output


def test_print_table_uses_rich_when_available(monkeypatch):
    """When Rich is present, formatting should use a table rather than raw text."""
    format_module = _reload_format_module(monkeypatch, rich_available=True)

    tasks = {
        "123": {
            "description": "read a book",
            "status": "done",
            "priority": "urgent",
            "created-at": "2026-08-22",
            "updated-at": "2026-08-23",
        }
    }

    format_module.print_table(tasks, ["123"])

    assert format_module.RICH_AVAILABLE is True
    assert len(types.SimpleNamespace().__dict__) == 0
    assert len(sys.modules["rich.console"].Console.instances) == 1
