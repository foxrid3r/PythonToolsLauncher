from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from .model import DEFAULT_ICON_COLOR, Tool, ToolStore, launch


def windows_uses_dark_theme() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0
    except OSError:
        return False


def palette() -> dict[str, str]:
    dark = windows_uses_dark_theme()
    return {
        "background": "#202124" if dark else "#F5F5F7",
        "surface": "#2B2C30" if dark else "#FFFFFF",
        "text": "#F5F5F7" if dark else "#1C1C1E",
        "muted": "#A9ABB0" if dark else "#6E6E73",
        "hover": "#34353A" if dark else "#E8E8ED",
        "border": "#48494E" if dark else "#C7C7CC",
        "accent": "#409CFF" if dark else "#3478F6",
    }


def resource_path(filename: str) -> Path:
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle / "assets" / filename


def apply_theme(root: tk.Tk, colors: dict[str, str]) -> None:
    root.configure(background=colors["background"])
    style = ttk.Style(root)
    if windows_uses_dark_theme():
        style.theme_use("clam")
    style.configure("Home.TFrame", background=colors["background"])
    style.configure(
        "Home.TLabel",
        background=colors["background"],
        foreground=colors["muted"],
    )
    style.configure("TFrame", background=colors["background"])
    style.configure(
        "TLabel", background=colors["background"], foreground=colors["text"]
    )
    style.configure(
        "TButton",
        background=colors["surface"],
        foreground=colors["text"],
        bordercolor=colors["border"],
        lightcolor=colors["surface"],
        darkcolor=colors["surface"],
        padding=(10, 6),
    )
    style.map(
        "TButton",
        background=[("active", colors["hover"]), ("pressed", colors["accent"])],
        foreground=[("pressed", "#FFFFFF")],
    )
    style.configure(
        "TEntry",
        fieldbackground=colors["surface"],
        foreground=colors["text"],
        insertcolor=colors["text"],
        bordercolor=colors["border"],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=colors["surface"],
        troughcolor=colors["background"],
        arrowcolor=colors["muted"],
    )
    root.option_add("*Menu.background", colors["surface"])
    root.option_add("*Menu.foreground", colors["text"])
    root.option_add("*Menu.activeBackground", colors["accent"])
    root.option_add("*Menu.activeForeground", "#FFFFFF")


class ToolDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, tool: Tool | None = None) -> None:
        super().__init__(parent)
        self.title("Edit Tool" if tool else "Add Tool")
        self.transient(parent)
        self.resizable(True, False)
        self.result: Tool | None = None
        self.tool_id = tool.id if tool else ""
        self.name = tk.StringVar(value=tool.name if tool else "")
        self.executable = tk.StringVar(value=tool.executable if tool else "")
        self.original_tool = tool
        self.icon_color = tool.icon_color if tool else DEFAULT_ICON_COLOR

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        for row, (label, variable) in enumerate(
            (
                ("Name", self.name),
                ("Program or script", self.executable),
            )
        ):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", pady=6)
            ttk.Entry(body, textvariable=variable, width=56).grid(
                row=row, column=1, sticky="ew", padx=(10, 8), pady=6
            )
        ttk.Button(body, text="Browse...", command=self._browse_executable).grid(
            row=1, column=2
        )
        ttk.Label(body, text="Icon color").grid(row=2, column=0, sticky="w", pady=6)
        self.color_preview = tk.Label(body, background=self.icon_color, width=4)
        self.color_preview.grid(row=2, column=1, sticky="w", padx=(10, 8), pady=6)
        ttk.Button(body, text="Choose...", command=self._choose_color).grid(
            row=2, column=2
        )
        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", command=self._save).pack(
            side="right", padx=(0, 8)
        )
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        self.grab_set()

    def _browse_executable(self) -> None:
        filename = filedialog.askopenfilename(
            parent=self,
            title="Choose a program or Python script",
            filetypes=(
                ("Programs and Python scripts", "*.exe *.com *.py *.pyw"),
                ("Python scripts", "*.py *.pyw"),
                ("Programs", "*.exe *.com"),
                ("All files", "*.*"),
            ),
        )
        if filename:
            self.executable.set(filename)
            if not self.name.get():
                self.name.set(Path(filename).stem)

    def _choose_color(self) -> None:
        _rgb, color = colorchooser.askcolor(
            color=self.icon_color, parent=self, title="Choose icon color"
        )
        if color:
            self.icon_color = color
            self.color_preview.configure(background=color)

    def _save(self) -> None:
        name = self.name.get().strip()
        executable = self.executable.get().strip().strip('"')
        if not name or not executable:
            messagebox.showerror(
                "Missing information",
                "Enter a name and choose a program or Python script.",
                parent=self,
            )
            return
        self.result = Tool(
            name=name,
            executable=executable,
            working_directory=self.original_tool.working_directory if self.original_tool else "",
            arguments=self.original_tool.arguments if self.original_tool else "",
            icon_color=self.icon_color,
            id=self.tool_id,
        )
        self.destroy()


class AppTile(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        tool: Tool,
        colors: dict[str, str],
        run_tool: object,
        show_menu: object,
    ) -> None:
        super().__init__(
            parent,
            width=142,
            height=148,
            background=colors["background"],
            highlightthickness=0,
            cursor="hand2",
            takefocus=True,
        )
        color = tool.icon_color
        red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        text_color = "#1C1C1E" if red * 299 + green * 587 + blue * 114 > 150000 else "white"
        initials = "".join(word[0] for word in tool.name.split()[:2]).upper() or "?"
        self._rounded(33, 7, 109, 83, 18, fill=color, outline="")
        self.create_text(
            71, 45, text=initials, fill=text_color, font=("Segoe UI Semibold", 23)
        )
        self.create_text(
            71,
            101,
            text=tool.name,
            fill=colors["text"],
            width=132,
            anchor="n",
            justify="center",
            font=("Segoe UI", 10),
        )
        if not tool.path.is_file():
            self.create_oval(93, 65, 109, 81, fill="#FF3B30", outline="white", width=2)
            self.create_text(101, 73, text="!", fill="white", font=("Segoe UI Semibold", 9))
        self.bind(
            "<Enter>",
            lambda _event: self.configure(background=colors["hover"]),
        )
        self.bind(
            "<Leave>",
            lambda _event: self.configure(background=colors["background"]),
        )
        self.bind("<Button-1>", lambda _event: run_tool(tool))
        self.bind("<Button-3>", lambda event: show_menu(tool, event))
        self.bind("<Return>", lambda _event: run_tool(tool))
        self.bind("<space>", lambda _event: run_tool(tool))

    def _rounded(
        self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: object
    ) -> int:
        points = (
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        )
        return self.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class Launcher:
    def __init__(self, root: tk.Tk, store: ToolStore | None = None) -> None:
        self.root = root
        self.store = store or ToolStore()
        self.colors = palette()
        self.selected_id = ""
        self.visible: list[Tool] = []
        self.pending_reflow = False
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar()
        root.title("Python Tools")
        root.geometry("820x560")
        root.minsize(480, 360)
        apply_theme(root, self.colors)
        self._build()
        try:
            self.store.load()
        except ValueError as exc:
            messagebox.showerror("Configuration error", str(exc), parent=root)
        self.refresh()

    def _build(self) -> None:
        body = ttk.Frame(self.root, padding=(24, 20, 24, 12), style="Home.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        header = ttk.Frame(body, style="Home.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Python Tools",
            background=self.colors["background"],
            foreground=self.colors["text"],
            font=("Segoe UI Semibold", 22),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="+  Add Tool", command=self.add).grid(row=0, column=1)
        self.search = ttk.Entry(body, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10), ipady=5)
        self.search_var.trace_add("write", lambda *_args: self.refresh())
        self.canvas = tk.Canvas(
            body, background=self.colors["background"], highlightthickness=0
        )
        self.canvas.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.tiles = ttk.Frame(self.canvas, style="Home.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.tiles, anchor="nw")
        self.tiles.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", self._schedule_reflow)
        self.canvas.bind(
            "<MouseWheel>",
            lambda event: self.canvas.yview_scroll(int(-event.delta / 120), "units"),
        )
        footer = ttk.Frame(body, style="Home.TFrame")
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(
            footer, text="Right-click a tool to edit or remove it", style="Home.TLabel"
        ).pack(side="left")
        ttk.Label(footer, textvariable=self.status_var, style="Home.TLabel").pack(side="right")
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="Open", command=self.run_selected)
        self.menu.add_separator()
        self.menu.add_command(label="Edit...", command=self.edit)
        self.menu.add_command(label="Move earlier", command=lambda: self.move(-1))
        self.menu.add_command(label="Move later", command=lambda: self.move(1))
        self.menu.add_separator()
        self.menu.add_command(label="Remove", command=self.remove)
        self.root.bind("<Control-f>", lambda _event: self.search.focus_set())
        self.root.bind("<Control-n>", lambda _event: self.add())
        self.root.bind("<Escape>", lambda _event: self.search_var.set(""))

    def selected(self) -> Tool | None:
        return next((tool for tool in self.store.tools if tool.id == self.selected_id), None)

    def refresh(self, selected_id: str = "") -> None:
        if selected_id:
            self.selected_id = selected_id
        query = self.search_var.get().casefold().strip()
        self.visible = [
            tool
            for tool in self.store.tools
            if not query
            or query in tool.name.casefold()
            or query in tool.executable.casefold()
        ]
        self.reflow()
        count = len(self.visible)
        self.status_var.set(f"{count} tool{'s' if count != 1 else ''}")

    def _schedule_reflow(self, _event: tk.Event[tk.Misc]) -> None:
        if not self.pending_reflow:
            self.pending_reflow = True
            self.root.after_idle(self.reflow)

    def reflow(self) -> None:
        self.pending_reflow = False
        for child in self.tiles.winfo_children():
            child.destroy()
        width = max(self.canvas.winfo_width(), 150)
        columns = max(1, width // 158)
        self.canvas.itemconfigure(self.window, width=width)
        # Grid keeps column options after the widgets in them are destroyed.
        # Clear obsolete weights/uniform groups before laying out a narrower grid.
        for column in range(self.tiles.grid_size()[0]):
            self.tiles.columnconfigure(column, weight=0, uniform="", minsize=0)
        for column in range(columns):
            self.tiles.columnconfigure(column, weight=1, uniform="apps")
        for index, tool in enumerate(self.visible):
            AppTile(
                self.tiles, tool, self.colors, self.run_tool, self.show_menu
            ).grid(
                row=index // columns,
                column=index % columns,
                padx=4,
                pady=(4, 10),
            )
        if not self.visible:
            empty = ttk.Frame(self.tiles, padding=40, style="Home.TFrame")
            empty.grid(row=0, column=0)
            ttk.Label(
                empty,
                text="No tools found",
                background=self.colors["background"],
                foreground=self.colors["muted"],
                font=("Segoe UI Semibold", 15),
            ).pack(pady=(30, 8))
            ttk.Button(empty, text="Add a tool", command=self.add).pack()

    def show_menu(self, tool: Tool, event: tk.Event[tk.Misc]) -> None:
        self.selected_id = tool.id
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def run_selected(self) -> None:
        tool = self.selected()
        if tool:
            self.run_tool(tool)

    def run_tool(self, tool: Tool) -> None:
        self.selected_id = tool.id
        try:
            launch(tool)
        except (OSError, ValueError) as exc:
            messagebox.showerror(f"Could not launch {tool.name}", str(exc), parent=self.root)

    def add(self) -> None:
        dialog = ToolDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.add(dialog.result)
            self.refresh(dialog.result.id)

    def edit(self) -> None:
        tool = self.selected()
        if not tool:
            return
        dialog = ToolDialog(self.root, tool)
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.update(dialog.result)
            self.refresh(dialog.result.id)

    def remove(self) -> None:
        tool = self.selected()
        if tool and messagebox.askyesno(
            "Remove tool",
            f'Remove "{tool.name}" from the launcher?\n\n'
            "The program or script will not be deleted.",
            parent=self.root,
        ):
            self.store.remove(tool.id)
            self.selected_id = ""
            self.refresh()

    def move(self, offset: int) -> None:
        tool = self.selected()
        if tool:
            self.store.move(tool.id, offset)
            self.refresh(tool.id)


def main() -> None:
    if os.name == "nt":
        try:
            from ctypes import windll

            windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "TrevorMcGregor.PythonToolsLauncher"
            )
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    icon = tk.PhotoImage(file=resource_path("launcher-icon.png"))
    root.iconphoto(True, icon)
    root._launcher_icon = icon
    Launcher(root)
    root.mainloop()
