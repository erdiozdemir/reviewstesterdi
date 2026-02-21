import tkinter as tk
from tkinter import font as tkfont
import requests
import threading
import webbrowser

#  CONSTANTS & THEME

BG       = "#F8FAFC"
CARD_BG  = "#FFFFFF"
ACCENT   = "#0D7C66"
ACCENT2  = "#1E6091"
TEXT     = "#1E293B"
SUBTEXT  = "#64748B"
ERROR    = "#DC2626"
HOVER_A  = "#0A6354"
HOVER_B  = "#174F72"
RADIUS   = 10

FIELDS = {
    "💻🧬  Bioinformatics": "bioinformatics OR computational biology OR NGS OR transcriptomics[MeSH Major Topic]",
    "🦠 Microbiology":   "microbiology OR microbiome OR bacterial genomics[MeSH Major Topic]",
    "🧬 Genetics": "genetics OR genomics OR whole genome sequencing OR GWAS[MeSH Major Topic]",
    "🛡️ Immunology": "immunology OR immune response OR T cell OR cytokine OR inflammation[MeSH Major Topic]",
    "🎗️ Cancer": "cancer OR oncology OR tumor OR carcinoma OR neoplasm[MeSH Major Topic]"
}


#  UTILITY HELPERS

def rounded_button(parent, text, command, bg, hover, width=260, height=52):
    """Creates a flat button with hover color change."""
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg="white", activebackground=hover, activeforeground="white",
        relief="flat", bd=0, cursor="hand2",
        font=("Segoe UI", 12, "bold"),
        width=1, height=1,
        padx=20, pady=12,
    )
    btn.configure(width=width // 10)   # approximate char width
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


#  PUBMED API

def fetch_articles(query: str, count: int = 10) -> list[dict]:
    """Fetches the most recent PubMed articles for a query."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # 1) Search → get IDs
    search_r = requests.get(
        f"{base}/esearch.fcgi",
        params={
            "db": "pubmed", "term": query,
            "retmax": count, "sort": "pub+date",
            "retmode": "json",
        },
        timeout=10,
    )
    search_r.raise_for_status()
    ids = search_r.json()["esearchresult"]["idlist"]

    if not ids:
        return []

    # 2) Summary → get metadata
    summary_r = requests.get(
        f"{base}/esummary.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        timeout=10,
    )
    summary_r.raise_for_status()
    data = summary_r.json()["result"]

    articles = []
    for uid in ids:
        item = data.get(uid, {})
        title   = item.get("title", "No title")
        authors = ", ".join(
            a.get("name", "") for a in item.get("authors", [])[:3]
        )
        if len(item.get("authors", [])) > 3:
            authors += " et al."
        journal = item.get("source", "")
        year    = item.get("pubdate", "")[:4]
        link    = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        articles.append({
            "title": title, "authors": authors,
            "journal": journal, "year": year, "link": link,
        })
    return articles



#  APPLICATION

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ReviewsInBio")
        self.geometry("700x620")
        self.minsize(600, 540)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.username = ""
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames: dict[str, tk.Frame] = {}
        self._show_login()


    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.frames = {}

    def _show_login(self):
        self._clear()
        frame = LoginScreen(self.container, self)
        frame.grid(row=0, column=0, sticky="nsew")

    def _show_home(self):
        self._clear()
        frame = HomeScreen(self.container, self)
        frame.grid(row=0, column=0, sticky="nsew")

    def _show_articles(self, field_label: str, query: str):
        self._clear()
        frame = ArticleScreen(self.container, self, field_label, query)
        frame.grid(row=0, column=0, sticky="nsew")



#  SCREEN 1 — LOGIN

class LoginScreen(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=BG)
        self.app = app
        self.columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        #Logo / Brand
        tk.Label(self, text="🔬", font=("Segoe UI", 52), bg=BG, fg=ACCENT).pack(pady=(60, 4))
        tk.Label(
            self, text="ReviewsInBio",
            font=("Segoe UI", 26, "bold"), bg=BG, fg=TEXT,
        ).pack()
        tk.Label(
            self, text="Explore the latest research in your field",
            font=("Segoe UI", 11), bg=BG, fg=SUBTEXT,
        ).pack(pady=(4, 40))

        #Card
        card = tk.Frame(self, bg=CARD_BG, padx=40, pady=36, relief="flat", bd=1)
        card.configure(highlightbackground="#E2E8F0", highlightthickness=1)
        card.pack(ipadx=10)

        tk.Label(card, text="Enter your name to get started",
                 font=("Segoe UI", 11), bg=CARD_BG, fg=SUBTEXT).pack(anchor="w")

        self.name_var = tk.StringVar()
        entry = tk.Entry(
            card, textvariable=self.name_var,
            font=("Segoe UI", 14), fg=TEXT,
            relief="solid", bd=1,
            highlightcolor=ACCENT, highlightthickness=1,
            width=26, insertbackground=ACCENT,
        )
        entry.pack(ipady=8, pady=(6, 4))
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._continue())

        self.err_label = tk.Label(card, text="", font=("Segoe UI", 10),
                                   bg=CARD_BG, fg=ERROR)
        self.err_label.pack(anchor="w", pady=(0, 8))

        btn = rounded_button(card, "Continue →", self._continue, ACCENT, HOVER_A)
        btn.pack(fill="x", pady=(4, 0))

    def _continue(self):
        name = self.name_var.get().strip()
        if not name:
            self.err_label.config(text="⚠  Please enter your name.")
            return
        self.app.username = name
        self.app._show_home()



#  SCREEN 2 — parts of home and field

_CARD_COLORS = [
    ("#0D7C66", "#0A6354"),
    ("#1E6091", "#174F72"),
    ("#6B3FA0", "#532E80"),
    ("#B5451B", "#8F3615"),
    ("#1D6A4A", "#155239"),
]

class HomeScreen(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=BG)
        self.app = app
        self.columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=ACCENT, padx=30, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ReviewsInBio",
                 font=("Segoe UI", 15, "bold"), bg=ACCENT, fg="white").pack(side="left")
        tk.Label(hdr, text=f"👤  {self.app.username}",
                 font=("Segoe UI", 11), bg=ACCENT, fg="#C7F9EE").pack(side="right")

        #partofwelcome
        tk.Label(
            self,
            text=f"Hello, {self.app.username}! 👋",
            font=("Segoe UI", 20, "bold"),
            bg=BG, fg=TEXT,
        ).pack(pady=(28, 4))
        tk.Label(
            self,
            text="Choose a research field to browse the latest articles",
            font=("Segoe UI", 11),
            bg=BG, fg=SUBTEXT,
        ).pack(pady=(0, 12))

        #Scrollable area
        scroll_wrapper = tk.Frame(self, bg=BG)
        scroll_wrapper.pack(fill="both", expand=True, padx=30, pady=(0, 8))

        canvas = tk.Canvas(scroll_wrapper, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(scroll_wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=self._inner, anchor="nw")

        def _on_inner(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas(e):
            canvas.itemconfig(win_id, width=e.width)
        def _on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        self._inner.bind("<Configure>", _on_inner)
        canvas.bind("<Configure>", _on_canvas)
        canvas.bind_all("<MouseWheel>", _on_wheel)

        #Field Cards
        for i, (label, query) in enumerate(FIELDS.items()):
            self._field_card(label, query, i)

        tk.Label(self, text="Powered by PubMed / NCBI",
                 font=("Segoe UI", 9), bg=BG, fg=SUBTEXT).pack(side="bottom", pady=6)

    def _field_card(self, label: str, query: str, index: int):
        color, hover = _CARD_COLORS[index % len(_CARD_COLORS)]

        card = tk.Frame(self._inner, bg=color, padx=28, pady=18, cursor="hand2")
        card.configure(highlightbackground=color, highlightthickness=1)
        card.pack(fill="x", pady=7)

        tk.Label(card, text=label, font=("Segoe UI", 14, "bold"),
                 bg=color, fg="white").pack(anchor="w")
        tk.Label(card, text="Click to see the 10 most recent PubMed articles →",
                 font=("Segoe UI", 10), bg=color, fg="#DFFFF8").pack(anchor="w", pady=(3, 0))

        for widget in (card, *card.winfo_children()):
            widget.bind("<Button-1>", lambda e, q=query, l=label: self.app._show_articles(l, q))
            widget.bind("<Enter>", lambda e, w=card: w.configure(bg=hover))
            widget.bind("<Leave>", lambda e, w=card, c=color: w.configure(bg=c))



#  SCREEN 3 — ARTICLE LIST
class ArticleScreen(tk.Frame):
    def __init__(self, parent, app: App, field_label: str, query: str):
        super().__init__(parent, bg=BG)
        self.app = app
        self.field_label = field_label
        self.query = query
        self.columnconfigure(0, weight=1)
        self._build()
        self._start_fetch()

    def _build(self):
        #Header
        hdr = tk.Frame(self, bg=ACCENT, padx=20, pady=14)
        hdr.pack(fill="x")
        back_btn = tk.Button(
            hdr, text="← Back", command=self.app._show_home,
            bg=ACCENT, fg="white", activebackground=HOVER_A, activeforeground="white",
            relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 10, "bold"),
        )
        back_btn.pack(side="left", padx=(0, 16))
        tk.Label(hdr, text=self.field_label, font=("Segoe UI", 14, "bold"),
                 bg=ACCENT, fg="white").pack(side="left")

        #Loading label
        self.status_label = tk.Label(
            self, text="⏳  Fetching latest articles from PubMed…",
            font=("Segoe UI", 12), bg=BG, fg=SUBTEXT,
        )
        self.status_label.pack(pady=40)

        #Scrollable canvas
        self.scroll_frame = tk.Frame(self, bg=BG)
        self.canvas = tk.Canvas(self.scroll_frame, bg=BG, highlightthickness=0)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        vsb = tk.Scrollbar(self.scroll_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.canvas_window, width=e.width)

    def _on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Fetch in background thread ───────────
    def _start_fetch(self):
        thread = threading.Thread(target=self._fetch_worker, daemon=True)
        thread.start()

    def _fetch_worker(self):
        try:
            articles = fetch_articles(self.query, count=10)
            self.after(0, lambda: self._render_articles(articles))
        except Exception as exc:
            self.after(0, lambda: self._render_error(str(exc)))

    # ── Render ────────────────────────────────
    def _render_articles(self, articles: list[dict]):
        self.status_label.destroy()
        if not articles:
            tk.Label(
                self.inner, text="No articles found.",
                font=("Segoe UI", 12), bg=BG, fg=SUBTEXT,
            ).pack(pady=40)
            return

        tk.Label(
            self.inner,
            text=f"  {len(articles)} most recent articles",
            font=("Segoe UI", 10, "bold"), bg=BG, fg=SUBTEXT, anchor="w",
        ).pack(fill="x", pady=(8, 4))

        for i, art in enumerate(articles, 1):
            self._article_card(i, art)

    def _article_card(self, index: int, art: dict):
        card = tk.Frame(
            self.inner, bg=CARD_BG, padx=18, pady=14,
            highlightbackground="#E2E8F0", highlightthickness=1,
        )
        card.pack(fill="x", pady=5)

        # Index badge
        badge_frame = tk.Frame(card, bg=ACCENT, width=28, height=28)
        badge_frame.pack(side="left", anchor="nw", padx=(0, 14))
        badge_frame.pack_propagate(False)
        tk.Label(badge_frame, text=str(index), font=("Segoe UI", 10, "bold"),
                 bg=ACCENT, fg="white").place(relx=0.5, rely=0.5, anchor="center")

        info = tk.Frame(card, bg=CARD_BG)
        info.pack(side="left", fill="both", expand=True)

        # Title (clickable link)
        title_lbl = tk.Label(
            info, text=art["title"],
            font=("Segoe UI", 11, "bold"), bg=CARD_BG, fg=ACCENT2,
            wraplength=480, justify="left", anchor="w", cursor="hand2",
        )
        title_lbl.pack(fill="x")
        title_lbl.bind("<Button-1>", lambda e, url=art["link"]: webbrowser.open(url))
        title_lbl.bind("<Enter>", lambda e, w=title_lbl: w.configure(fg=HOVER_B))
        title_lbl.bind("<Leave>", lambda e, w=title_lbl: w.configure(fg=ACCENT2))

        # Meta row
        meta = f"{art['authors']}   |   {art['journal']}   {art['year']}"
        tk.Label(
            info, text=meta,
            font=("Segoe UI", 9), bg=CARD_BG, fg=SUBTEXT,
            wraplength=480, justify="left", anchor="w",
        ).pack(fill="x", pady=(3, 0))

        # PubMed link
        link_lbl = tk.Label(
            info, text="🔗 View on PubMed",
            font=("Segoe UI", 9, "underline"), bg=CARD_BG, fg=ACCENT,
            cursor="hand2", anchor="w",
        )
        link_lbl.pack(anchor="w", pady=(4, 0))
        link_lbl.bind("<Button-1>", lambda e, url=art["link"]: webbrowser.open(url))

    def _render_error(self, msg: str):
        self.status_label.config(
            text=f"❌  Error fetching articles:\n{msg}",
            fg=ERROR, font=("Segoe UI", 11),
        )


#  ENTRY POINT

if __name__ == "__main__":
    app = App()
    app.mainloop()