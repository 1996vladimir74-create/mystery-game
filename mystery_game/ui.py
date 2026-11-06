import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime
from .config import *
from .core import DataManager, DataError, SaveManager, SaveError, AudioManager, normalize_answer
from .data import ensure_default, DLCManager
from .images import ImageAssets
import json

class InventoryWindow(tk.Toplevel):
    def __init__(self, parent, inventory, image_assets=None):
        super().__init__(parent); self.title("Инвентарь улик"); self.geometry("560x440")
        self.configure(bg="#18212a"); self.transient(parent); self.image_assets=image_assets
        ttk.Label(self, text="СОБРАННЫЕ УЛИКИ", style="Title.TLabel").pack(pady=18)
        body=ttk.Frame(self,padding=16); body.pack(fill="both",expand=True)
        if not inventory: ttk.Label(body,text="Пока нет найденных предметов.").pack(pady=25)
        for item in inventory:
            card=ttk.LabelFrame(body,text=f"{item.get('icon','•')}  {item.get('name','Улика')}",padding=10)
            card.pack(fill="x",pady=6)
            media=ttk.Frame(card); media.pack(fill="x",anchor="w")
            image_path=item.get("item_image")
            photo=self.image_assets.load(image_path,(150,150)) if self.image_assets and image_path else None
            if photo:
                image_label=ttk.Label(media,image=photo); image_label.image=photo; image_label.pack(side="left",padx=(0,12),pady=4)
            ttk.Label(media,text=item.get("description","Описание отсутствует."),wraplength=310,justify="left").pack(side="left",anchor="n",pady=4)
            if item.get("story"):
                ttk.Label(card,text="Из материалов дела:",font=("Arial",9,"bold")).pack(anchor="w",pady=(8,2))
                ttk.Label(card,text=item["story"],wraplength=480).pack(anchor="w")
        ttk.Button(self,text="Закрыть",command=self.destroy).pack(pady=14)

class SettingsWindow(tk.Toplevel):
    def __init__(self,parent,settings,on_save):
        super().__init__(parent); self.title("Настройки"); self.geometry("440x430")
        self.transient(parent); self.settings=dict(settings); self.on_save=on_save
        ttk.Label(self,text="НАСТРОЙКИ",style="Title.TLabel").pack(pady=16)
        form=ttk.Frame(self,padding=20); form.pack(fill="both",expand=True)
        self.sound=tk.BooleanVar(value=self.settings.get("sound_enabled",True))
        self.music=tk.BooleanVar(value=self.settings.get("music_enabled",True))
        self.anim=tk.BooleanVar(value=self.settings.get("animations",True))
        self.diff=tk.StringVar(value=self.settings.get("difficulty","normal"))
        ttk.Checkbutton(form,text="Звуковые эффекты",variable=self.sound).pack(anchor="w",pady=7)
        ttk.Checkbutton(form,text="Фоновая музыка (если добавлен файл)",variable=self.music).pack(anchor="w",pady=7)
        ttk.Checkbutton(form,text="Анимации интерфейса",variable=self.anim).pack(anchor="w",pady=7)
        ttk.Label(form,text="Громкость музыки").pack(anchor="w",pady=(14,2))
        self.volume=tk.DoubleVar(value=float(self.settings.get("music_volume",.35)))
        ttk.Scale(form,from_=0,to=1,variable=self.volume).pack(fill="x")
        ttk.Label(form,text="Размер текста").pack(anchor="w",pady=(12,2))
        self.font_scale=tk.DoubleVar(value=float(self.settings.get("font_scale",1.0)))
        ttk.Scale(form,from_=.8,to=1.4,variable=self.font_scale).pack(fill="x")
        ttk.Label(form,text="Сложность подсказок").pack(anchor="w",pady=(14,2))
        ttk.Combobox(form,textvariable=self.diff,values=("easy","normal","hard"),state="readonly").pack(fill="x")
        ttk.Button(self,text="Сохранить настройки",command=self.save).pack(pady=12)
        ttk.Button(self,text="Редактор расследований",command=parent.open_editor).pack(fill="x",padx=24,pady=4)
        ttk.Button(self,text="Редактор DLC",command=parent.open_dlc_editor).pack(fill="x",padx=24,pady=4)
    def save(self):
        self.settings.update(sound_enabled=self.sound.get(),music_enabled=self.music.get(),
          animations=self.anim.get(),music_volume=self.volume.get(),font_scale=self.font_scale.get(),difficulty=self.diff.get())
        self.on_save(self.settings); self.destroy()

class EditorWindow(tk.Toplevel):
    def __init__(self,parent,manager,on_saved):
        super().__init__(parent); self.title("Редактор расследований"); self.geometry("900x680")
        self.manager=manager; self.on_saved=on_saved
        ttk.Label(self,text="РЕДАКТОР РАССЛЕДОВАНИЙ",style="Title.TLabel").pack(pady=12)
        ttk.Label(self,text="Редактируй JSON: тексты, подсказки и пути к изображениям (cover_image, background_image, document_image, illustration_image, item_image). Пути задаются от assets/images/.").pack(pady=5)
        self.text=tk.Text(self,wrap="none",font=("Consolas",10),bg="#101820",fg="#f2eadf",insertbackground="white",undo=True)
        self.text.pack(fill="both",expand=True,padx=16,pady=12)
        try:
            import json
            self.text.insert("1.0",json.dumps(manager.load_cases(),ensure_ascii=False,indent=2))
        except DataError as exc: messagebox.showerror("Ошибка данных",str(exc),parent=self)
        ttk.Button(self,text="Проверить и сохранить",command=self.save).pack(pady=12)
    def save(self):
        import json
        try:
            cases=json.loads(self.text.get("1.0","end-1c"))
            if not isinstance(cases,list) or not cases: raise DataError("Ожидается непустой JSON-список.")
            ids=[case.get("id") for case in cases]
            if len(ids)!=len(set(ids)): raise DataError("ID расследований должны быть уникальными.")
            self.manager.save_cases(cases); self.on_saved()
            messagebox.showinfo("Готово","Расследования сохранены.",parent=self)
        except (json.JSONDecodeError,DataError,AttributeError,TypeError) as exc:
            messagebox.showerror("Не удалось сохранить",str(exc),parent=self)

class DLCEditorWindow(tk.Toplevel):
    def __init__(self,parent,manager,on_saved):
        super().__init__(parent); self.title("Редактор DLC"); self.geometry("760x560")
        self.manager=manager; self.on_saved=on_saved
        ttk.Label(self,text="РЕДАКТОР ИСТОРИЙ / DLC",style="Title.TLabel").pack(pady=12)
        ttk.Label(self,text="Каждый DLC содержит последовательный список ID расследований из редактора расследований.").pack(pady=4)
        self.text=tk.Text(self,wrap="none",font=("Consolas",10),bg="#101820",fg="#f2eadf",insertbackground="white",undo=True)
        self.text.pack(fill="both",expand=True,padx=14,pady=10)
        self.text.insert("1.0",json.dumps(manager.load_dlcs(),ensure_ascii=False,indent=2))
        buttons=ttk.Frame(self); buttons.pack(fill="x",padx=14,pady=10)
        ttk.Button(buttons,text="＋ Добавить DLC в начало списка",command=self.add_dlc).pack(side="left")
        ttk.Button(buttons,text="Проверить и сохранить",command=self.save).pack(side="right")

    def add_dlc(self):
        title=simpledialog.askstring("Новое DLC","Название истории:",parent=self)
        if not title or not title.strip():return
        description=simpledialog.askstring("Описание","Краткое описание истории:",parent=self) or ""
        quest_text=simpledialog.askstring(
            "Цепочка квестов","Введи ID расследований через запятую, в нужном порядке:",parent=self
        )
        if not quest_text:return
        quests=[value.strip() for value in quest_text.split(",") if value.strip()]
        dlcs=json.loads(self.text.get("1.0","end-1c"))
        dlcs.insert(0,{
            "id":"dlc-"+datetime.now().strftime("%Y%m%d%H%M%S"),
            "title":title.strip(),"description":description.strip(),
            "added_at":datetime.now().isoformat(timespec="seconds"),"quests":quests
        })
        self.text.delete("1.0","end")
        self.text.insert("1.0",json.dumps(dlcs,ensure_ascii=False,indent=2))

    def save(self):
        try:
            dlcs=json.loads(self.text.get("1.0","end-1c"))
            self.manager.save_dlcs(dlcs); self.on_saved()
            messagebox.showinfo("Готово","Список DLC сохранён. Новые истории отображаются первыми.",parent=self)
        except (json.JSONDecodeError,DataError,TypeError) as exc:
            messagebox.showerror("Ошибка DLC",str(exc),parent=self)


class MysteryGameApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_TITLE); self.geometry(WINDOW_SIZE); self.minsize(820,600)
        self.configure(bg="#18212a")
        for folder in (DATA_DIR,ASSETS_DIR,SOUNDS_DIR,SAVES_DIR): folder.mkdir(parents=True,exist_ok=True)
        ensure_default(INVESTIGATIONS_FILE, BUNDLED_INVESTIGATIONS_FILE)
        ensure_default(DLCS_FILE, BUNDLED_DLCS_FILE)
        self.data_manager=DataManager(INVESTIGATIONS_FILE)
        try: self.cases=self.data_manager.load_cases()
        except DataError as exc:
            messagebox.showerror("Ошибка данных",str(exc)); self.destroy(); raise
        self.dlc_manager=DLCManager(DLCS_FILE, self.data_manager.load_cases)
        try: self.dlcs=self.dlc_manager.load_dlcs()
        except DataError as exc:
            messagebox.showerror("Ошибка DLC",str(exc)); self.destroy(); raise
        self.save_manager=SaveManager(SAVES_DIR); self.settings=self.save_manager.load_settings()
        self.theme=self._load_theme(); self.image_assets=ImageAssets(ASSETS_DIR)
        self.configure(bg=self.theme.get("colors",{}).get("window","#18212a"))
        self.audio=AudioManager(SOUNDS_DIR,self.settings); self.active_save=None
        self._styles()
        root=ttk.Frame(self,style="Background.TFrame"); root.pack(fill="both",expand=True)
        root.rowconfigure(0,weight=1); root.columnconfigure(0,weight=1)
        self.menu=ttk.Frame(root,style="Background.TFrame",padding=40)
        self.game=ttk.Frame(root,style="Background.TFrame",padding=28)
        self.board=ttk.Frame(root,style="Background.TFrame",padding=28)
        for frame in (self.menu,self.game,self.board): frame.grid(row=0,column=0,sticky="nsew")
        self._build_menu(); self._build_game(); self._build_board()
        self._animation_job=None; self._animation_phase=False; self.show("menu"); self.audio.music(); self.protocol("WM_DELETE_WINDOW",self.on_close)

    def _load_theme(self):
        defaults={"colors":{},"fonts":{},"images":{}}
        try:
            loaded=json.loads(THEME_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded,dict):
                for key in defaults:
                    if isinstance(loaded.get(key),dict): defaults[key].update(loaded[key])
        except (OSError,ValueError,TypeError): pass
        return defaults

    def _styles(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except tk.TclError:pass
        scale=float(getattr(self,"settings",{}).get("font_scale",1.0)); colors=self.theme.get("colors",{}); fonts=self.theme.get("fonts",{})
        window=colors.get("window","#18212a"); panel=colors.get("panel","#202d38"); paper=colors.get("paper","#f2eadf")
        accent=colors.get("accent","#e8c99a"); muted=colors.get("muted","#c7c0b6")
        body=fonts.get("body","Arial"); display=fonts.get("display","Times New Roman"); typewriter=fonts.get("typewriter","Courier New"); story=fonts.get("story","Georgia")
        s.configure(".",font=(body,max(9,int(11*scale))))
        s.configure("Background.TFrame",background=window)
        s.configure("TFrame",background=panel)
        s.configure("TLabel",background=panel,foreground=paper)
        s.configure("Title.TLabel",font=(display,max(18,int(22*scale)),"bold"),background=window,foreground=accent)
        s.configure("Hero.TLabel",font=(display,max(22,int(30*scale)),"bold"),background=window,foreground=paper)
        s.configure("Eyebrow.TLabel",font=(typewriter,13,"bold"),background=window,foreground=colors.get("accent_detail","#c99b68"))
        s.configure("Subtitle.TLabel",font=(story,12),background=window,foreground=muted)
        s.configure("Footer.TLabel",background=window,foreground=colors.get("footer","#a9a39a"))
        s.configure("Task.TLabel",font=(story,17),background=panel,foreground=colors.get("task","#fff7e8"))
        s.configure("Story.TLabel",font=(story,12),background=panel,foreground=colors.get("story","#c9c1b6"))
        s.configure("Hint.TLabel",background=panel,foreground=accent)
        s.configure("TButton",padding=9,background=colors.get("button","#8b6545"),foreground=paper)
        s.map("TButton",background=[("active",colors.get("button_active","#a77c55"))])

    def _build_menu(self):
        # The portrait artwork occupies the left side; the DLC launcher is a separate right panel.
        bg=self.image_assets.load_fit(self.theme.get("images",{}).get("menu_background"),(530,700),centering=(0.5,0.22))
        self.menu_art=tk.Label(self.menu,bg="#17231f",borderwidth=0)
        if bg:
            self.menu_art.configure(image=bg); self.menu_art.image=bg
        self.menu_art.place(x=0,y=0,width=530,height=700)
        self.active_dlc_title=tk.Label(
            self.menu,text="Выбери историю справа",bg="#17231f",fg="#f0d5a7",
            font=("Georgia",15,"bold"),wraplength=450,justify="left"
        )
        self.active_dlc_title.place(x=24,y=205,width=470)
        self.menu_panel=tk.Frame(self.menu,bg="#172b28",highlightthickness=1,highlightbackground="#9b7951")
        self.menu_panel.place(relx=0.53,rely=0,relwidth=0.47,relheight=1)
        tk.Label(self.menu_panel,text="ИСТОРИИ  /  DLC",bg="#172b28",fg="#e8c99a",
                 font=("Courier New",15,"bold")).pack(anchor="w",padx=24,pady=(38,12))
        self.dlc_list=tk.Listbox(
            self.menu_panel,bg="#20332f",fg="#f2eadf",selectbackground="#8b6545",
            selectforeground="#fff7e8",font=("Georgia",12),relief="flat",
            highlightthickness=1,highlightbackground="#8b765c",activestyle="none",
            exportselection=False
        )
        self.dlc_list.pack(fill="x",padx=24,ipady=8)
        self.dlc_list.bind("<<ListboxSelect>>",self._on_dlc_selected)
        self._populate_dlc_list()
        ttk.Separator(self.menu_panel).pack(fill="x",padx=24,pady=(24,14))
        actions=tk.Frame(self.menu_panel,bg="#172b28")
        actions.pack(fill="x",padx=24)
        for label,cmd in (
            ("Загрузка",self.continue_game),
            ("Опции",self.open_settings),
            ("Доска раскрытых дел",self.show_board),
            ("Выход",self.on_close)
        ):
            button=tk.Button(
                actions,text=label,command=cmd,anchor="w",relief="flat",
                bg="#263c36",fg="#f2eadf",activebackground="#8b6545",
                activeforeground="#fff7e8",font=("Georgia",12),padx=14,pady=11,
                cursor="hand2"
            )
            button.pack(fill="x",pady=5)
        tk.Label(self.menu_panel,text="ANASTASIA DAYS  •  PRIVATE STORIES",
                 bg="#172b28",fg="#b9a78d",font=("Courier New",8)).pack(side="bottom",pady=18)

    def _populate_dlc_list(self):
        self.dlc_list.delete(0,"end")
        for dlc in self.dlcs:
            self.dlc_list.insert("end",dlc["title"])
        if self.dlcs:
            self.dlc_list.selection_clear(0,"end")

    def _on_dlc_selected(self,_event=None):
        selection=self.dlc_list.curselection()
        if not selection:return
        dlc=self.dlcs[selection[0]]
        self.active_dlc_title.configure(text=dlc["title"])
        if messagebox.askyesno("Начать DLC",f"Начать историю «{dlc['title']}»?\n\nКвесты будут проходиться последовательно.",parent=self):
            self.start_dlc(dlc)

    def start_dlc(self,dlc):
        cases={case["id"]:case for case in self.cases}
        quest_ids=list(dlc["quests"])
        first=cases[quest_ids[0]]
        name=simpledialog.askstring("Новая история","Название сохранения:",initialvalue=dlc["title"],parent=self)
        if not name or not name.strip():
            self.dlc_list.selection_clear(0,"end")
            return
        self.active_save=self.save_manager.create(name.strip(),first["id"])
        self.active_save.update(
            dlc_id=dlc["id"],dlc_title=dlc["title"],quest_ids=quest_ids,
            completed_case_ids=[],completed_case_titles={},case_title=first["title"]
        )
        self.persist()
        self.show("game")

    def _build_game(self):
        self.case_background=tk.Label(self.game,borderwidth=0,bg=self.theme.get("colors",{}).get("window","#18212a"))
        self.case_background.place(relx=0,rely=0,relwidth=1,relheight=1); self.case_background.lower()
        head=ttk.Frame(self.game,style="Background.TFrame"); head.pack(fill="x")
        self.case_title=ttk.Label(head,text="",style="Eyebrow.TLabel"); self.case_title.pack(side="left")
        ttk.Button(head,text="В меню",command=self.back_to_menu).pack(side="right")
        ttk.Label(self.game,text="ДОСЬЕ РАССЛЕДОВАНИЯ",style="Hero.TLabel").pack(pady=(18,4))
        self.progress=ttk.Label(self.game,text="",style="Subtitle.TLabel"); self.progress.pack(pady=(0,10))
        self.case_art=ttk.Label(self.game,style="Background.TFrame"); self.case_art.pack(pady=(0,8))
        media=ttk.Frame(self.game,style="Background.TFrame"); media.pack(fill="x",padx=24,pady=(0,8))
        self.clue_art=ttk.Label(media,style="Background.TFrame"); self.clue_art.pack(side="left",expand=True,padx=5)
        self.document_art=ttk.Label(media,style="Background.TFrame"); self.document_art.pack(side="left",expand=True,padx=5)
        panel=ttk.LabelFrame(self.game,text="Текущая улика",padding=22); panel.pack(fill="both",expand=True,padx=24)
        self.task=ttk.Label(panel,text="",style="Task.TLabel",wraplength=760,justify="left"); self.task.pack(anchor="w",pady=(4,16))
        self.story=ttk.Label(panel,text="",style="Story.TLabel",wraplength=760,justify="left"); self.story.pack(anchor="w",pady=(0,18))
        self.answer=tk.StringVar(); self.entry=ttk.Entry(panel,textvariable=self.answer,font=("Arial",14))
        self.entry.pack(fill="x",pady=8); self.entry.bind("<Return>",lambda _e:self.check_answer())
        actions=ttk.Frame(panel); actions.pack(fill="x",pady=10)
        ttk.Button(actions,text="Проверить ответ",command=self.check_answer).pack(side="left",padx=(0,8))
        ttk.Button(actions,text="Подсказка",command=self.show_hint).pack(side="left",padx=8)
        ttk.Button(actions,text="Инвентарь",command=self.show_inventory).pack(side="left",padx=8)
        self.hint_label=ttk.Label(panel,text="",style="Hint.TLabel",wraplength=760); self.hint_label.pack(anchor="w",pady=12)
        foot=ttk.Frame(self.game,style="Background.TFrame"); foot.pack(fill="x",pady=(16,0))
        self.inventory_summary=ttk.Label(foot,text="Инвентарь: пусто",style="Footer.TLabel"); self.inventory_summary.pack(side="left")
        ttk.Label(foot,text="Автосохранение включено",style="Footer.TLabel").pack(side="right")

    def _build_board(self):
        top=ttk.Frame(self.board,style="Background.TFrame"); top.pack(fill="x")
        ttk.Button(top,text="← В меню",command=self.back_to_menu).pack(side="left")
        ttk.Label(self.board,text="ДОСКА РАСКРЫТЫХ ДЕЛ",style="Hero.TLabel").pack(pady=24)
        self.board_canvas=tk.Canvas(self.board,bg="#9a7048",highlightthickness=0)
        self.board_canvas.pack(fill="both",expand=True,padx=10,pady=10)
        self.board_inner=ttk.Frame(self.board_canvas)
        self.board_canvas.create_window((12,12),window=self.board_inner,anchor="nw")
        self.board_inner.bind("<Configure>",lambda _e:self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all")))

    def show(self,name):
        {"menu":self.menu,"game":self.game,"board":self.board}[name].tkraise()
        if name=="menu":
            self.continue_btn.configure(state="normal" if self.save_manager.latest_incomplete() else "disabled")
            self._start_menu_animation()
        else: self._stop_menu_animation()
        if name=="game" and self.active_save:self.refresh_game()
        if name=="board":self.refresh_board()

    def _start_menu_animation(self):
        self._stop_menu_animation()
        if self.settings.get("animations", True): self._animate_menu()
    def _animate_menu(self):
        if not self.winfo_exists() or not self.settings.get("animations", True): return
        self._animation_phase = not self._animation_phase
        self.menu_status.configure(foreground="#e8c99a" if self._animation_phase else "#a9a39a")
        self._animation_job = self.after(1100, self._animate_menu)
    def _stop_menu_animation(self):
        if self._animation_job is not None:
            try: self.after_cancel(self._animation_job)
            except tk.TclError: pass
            self._animation_job = None

    def get_case(self):
        if not self.active_save:
            raise SaveError("Нет активного сохранения.")
        case = next((c for c in self.cases if c["id"] == self.active_save.get("case_id")), None)
        if case is None:
            raise SaveError("Расследование из сохранения отсутствует в текущем файле данных. Верни прежний JSON-файл или выбери другое сохранение.")
        return case

    def new_game(self):
        choices=[c for c in self.cases if not c.get("locked",False)]
        if not choices: messagebox.showinfo("Нет дел","Добавь расследование в редакторе.",parent=self); return
        if len(choices)==1: case=choices[0]
        else:
            labels="\n".join(f"{i+1}. {c['title']}" for i,c in enumerate(choices))
            n=simpledialog.askinteger("Выбор дела",f"Выбери номер:\n{labels}",minvalue=1,maxvalue=len(choices),parent=self)
            if n is None:return
            case=choices[n-1]
        name=simpledialog.askstring("Новое расследование","Название сохранения:",parent=self)
        if not name or not name.strip():return
        self.active_save=self.save_manager.create(name.strip(),case["id"])
        self.active_save["case_title"]=case["title"]; self.persist(); self.show("game")

    def continue_game(self):
        saves=[item for item in self.save_manager.list_saves() if not item.get("completed")]
        if not saves:
            messagebox.showinfo("Нет сохранений","Нет незавершённых расследований.",parent=self)
            return
        if len(saves)==1:
            item=saves[0]
        else:
            labels="\n".join(f"{i+1}. {x['name']} — {x.get('case_title',x['case_id'])} — {x.get('updated_at','')[:16]}" for i,x in enumerate(saves))
            choice=simpledialog.askinteger("Продолжить расследование",f"Выбери сохранение:\\n{labels}",
                                           minvalue=1,maxvalue=len(saves),parent=self)
            if choice is None:return
            item=saves[choice-1]
        try:
            self.active_save=self.save_manager.load(item["id"])
            self.get_case()
            self.show("game")
        except SaveError as exc:
            messagebox.showerror("Ошибка сохранения",str(exc),parent=self)

    def refresh_game(self):
        case=self.get_case(); i=self.active_save["current_clue"]
        if i>=len(case["clues"]): self.finish_case(); return
        clue=case["clues"][i]; self.case_title.configure(text=case["title"])
        self._display_image(self.case_background,case.get("background_image"),(1000,700),"case_background")
        self._display_image(self.case_art,case.get("cover_image"),(720,90),"case_art")
        self._display_image(self.clue_art,clue.get("illustration_image"),(300,120),"clue_art")
        self._display_image(self.document_art,clue.get("document_image") or case.get("document_image"),(300,120),"document_art")
        self.progress.configure(text=f"УЛИКА {i+1} ИЗ {len(case['clues'])}")
        self.task.configure(text=clue["task"]); self.story.configure(text=clue.get("story",""))
        self.answer.set(""); self.hint_label.configure(text="")
        self.inventory_summary.configure(text=f"Найдено предметов: {len(self.active_save.get('inventory',[]))}")
        self.entry.focus_set()

    def _display_image(self, widget, relative_path, size, ref_name):
        photo=self.image_assets.load(relative_path,size) if relative_path else None
        setattr(self,ref_name+"_photo",photo)
        placeholders={"case_art":"ОБЛОЖКА ДЕЛА — добавь cover_image","clue_art":"ИЛЛЮСТРАЦИЯ УЛИКИ — добавь illustration_image","document_art":"ФОТО / ДОКУМЕНТ — добавь document_image"}
        widget.configure(image=photo if photo else "",text="" if photo else placeholders.get(ref_name,""))

    def submit_answer(self,raw):
        case=self.get_case(); i=self.active_save["current_clue"]; clue=case["clues"][i]
        valid={normalize_answer(x) for x in clue["answers"]}
        normalized = normalize_answer(raw)
        if not normalized or normalized not in valid:return False
        self.active_save.setdefault("inventory",[]).append({"name":clue.get("item_name",f"Улика №{i+1}"),
          "icon":clue.get("icon","🔎"),"description":clue.get("item_description",clue.get("story","")),
          "story":clue.get("story",""),"item_image":clue.get("item_image"),"clue_number":i+1})
        self.active_save["current_clue"]+=1; self.active_save["hints_used"]=0
        if self.active_save["current_clue"]>=len(case["clues"]):self.finish_case()
        else:self.persist()
        return True

    def check_answer(self):
        if not self.answer.get().strip():
            messagebox.showinfo("Ответ", "Сначала введи ответ.", parent=self)
            return
        clue_index = self.active_save["current_clue"]
        clue = self.get_case()["clues"][clue_index]
        if self.submit_answer(self.answer.get()):
            self.audio.effect("clue.wav")
            if self.active_save and not self.active_save.get("completed"):
                discovery = clue.get("discovery_message") or (
                    f"Улика «{clue.get('item_name', 'Найденный предмет')}» добавлена в инвентарь.\n\n"
                    f"{clue.get('story', 'Расследование продолжается.')}"
                )
                messagebox.showinfo("Улика найдена", discovery, parent=self)
                self.refresh_game()
        else:
            self.audio.effect("wrong.wav")
            messagebox.showwarning(
                "Пока неверно",
                "Попробуй другую формулировку или воспользуйся подсказкой.",
                parent=self
            )

    def show_hint(self):
        clue=self.get_case()["clues"][self.active_save["current_clue"]]; hints=clue.get("hints",[])
        used=self.active_save.get("hints_used",0); difficulty=self.settings.get("difficulty","normal")
        limit={"easy":len(hints),"normal":min(2,len(hints)),"hard":1}.get(difficulty,2)
        if not hints:self.hint_label.configure(text="Для этой улики подсказок нет.");return
        if used>=limit:self.hint_label.configure(text="Лимит подсказок для выбранной сложности исчерпан.");return
        self.hint_label.configure(text=f"Подсказка {used+1}: {hints[min(used,len(hints)-1)]}")
        self.active_save["hints_used"]=used+1;self.persist()

    def show_inventory(self):InventoryWindow(self,self.active_save.get("inventory",[]),self.image_assets)

    def finish_case(self):
        case=self.get_case()
        completed_ids=self.active_save.setdefault("completed_case_ids",[])
        completed_titles=self.active_save.setdefault("completed_case_titles",{})
        if case["id"] not in completed_ids:
            completed_ids.append(case["id"])
        completed_titles[case["id"]]=case["title"]
        quest_ids=self.active_save.get("quest_ids",[case["id"]])
        try: current_index=quest_ids.index(case["id"])
        except ValueError: current_index=len(quest_ids)-1
        self.audio.effect("success.wav")
        if current_index+1 < len(quest_ids):
            next_id=quest_ids[current_index+1]
            next_case=next((item for item in self.cases if item["id"]==next_id),None)
            if next_case is None:
                messagebox.showerror("Ошибка DLC",f"Следующий квест «{next_id}» отсутствует.",parent=self)
                return
            self.active_save.update(case_id=next_id,case_title=next_case["title"],current_clue=0,hints_used=0)
            self.persist()
            messagebox.showinfo(
                "Этап раскрыт",
                f"«{case['title']}» завершено.\n\nСледующий квест: «{next_case['title']}».\n\n{case.get('final_letter','')}",
                parent=self
            )
            self.show("game")
            return
        self.active_save["completed"]=True
        self.active_save["case_title"]=self.active_save.get("dlc_title",case["title"])
        self.active_save["completed_at"]=datetime.now().isoformat(timespec="seconds")
        self.persist()
        messagebox.showinfo("История раскрыта",case.get("final_letter","История раскрыта!"),parent=self)
        self.show("board")

    def persist(self):
        if self.active_save:
            try:self.save_manager.save(self.active_save)
            except SaveError as exc:messagebox.showerror("Ошибка сохранения",str(exc),parent=self)

    def refresh_board(self):
        for child in self.board_inner.winfo_children():child.destroy()
        cases=self.save_manager.completed_cases()
        if not cases:ttk.Label(self.board_inner,text="Пока нет закрытых дел. Первое расследование ждёт тебя!").pack(padx=30,pady=30);return
        for item in cases:
            card=ttk.LabelFrame(self.board_inner,text="📌 ДОСЬЕ ЗАКРЫТО",padding=18);card.pack(side="left",padx=12,pady=12,anchor="n")
            ttk.Label(card,text=item["name"],font=("Courier New",12,"bold"),wraplength=210).pack(pady=5)
            ttk.Label(card,text=f"Завершено: {item.get('completed_at','')[:10]}").pack()
            ttk.Label(card,text="✓ Дело раскрыто").pack(pady=5)

    def back_to_menu(self):self.persist();self.show("menu")
    def show_board(self):self.show("board")
    def open_settings(self):SettingsWindow(self,self.settings,self.update_settings)
    def update_settings(self,settings):
        self.settings=settings;self.save_manager.save_settings(settings);self.audio.apply(settings);self._styles()
        if settings.get("music_enabled"):self.audio.music()
        else:self.audio.stop()
    def open_editor(self):EditorWindow(self,self.data_manager,self.reload_cases)
    def open_dlc_editor(self):DLCEditorWindow(self,self.dlc_manager,self.reload_dlcs)
    def reload_cases(self):
        try:
            self.cases=self.data_manager.load_cases()
            self.reload_dlcs()
        except DataError as exc:messagebox.showerror("Ошибка",str(exc),parent=self)
    def reload_dlcs(self):
        try:
            self.dlcs=self.dlc_manager.load_dlcs()
            self._populate_dlc_list()
        except DataError as exc:messagebox.showerror("Ошибка DLC",str(exc),parent=self)
    def on_close(self):
        self.persist();self._stop_menu_animation();self.audio.close();self.destroy()
