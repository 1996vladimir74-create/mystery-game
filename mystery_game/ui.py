import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime
from .config import *
from .core import DataManager, DataError, SaveManager, SaveError, AudioManager, normalize_answer
from .data import ensure_default

class InventoryWindow(tk.Toplevel):
    def __init__(self, parent, inventory):
        super().__init__(parent); self.title("Инвентарь улик"); self.geometry("560x440")
        self.configure(bg="#18212a"); self.transient(parent)
        ttk.Label(self, text="СОБРАННЫЕ УЛИКИ", style="Title.TLabel").pack(pady=18)
        body=ttk.Frame(self,padding=16); body.pack(fill="both",expand=True)
        if not inventory: ttk.Label(body,text="Пока нет найденных предметов.").pack(pady=25)
        for item in inventory:
            card=ttk.LabelFrame(body,text=f"{item.get('icon','•')}  {item.get('name','Улика')}",padding=10)
            card.pack(fill="x",pady=6)
            ttk.Label(card,text=item.get("description","Описание отсутствует."),wraplength=480).pack(anchor="w")
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
        ttk.Button(self,text="Сохранить настройки",command=self.save).pack(pady=16)
    def save(self):
        self.settings.update(sound_enabled=self.sound.get(),music_enabled=self.music.get(),
          animations=self.anim.get(),music_volume=self.volume.get(),font_scale=self.font_scale.get(),difficulty=self.diff.get())
        self.on_save(self.settings); self.destroy()

class EditorWindow(tk.Toplevel):
    def __init__(self,parent,manager,on_saved):
        super().__init__(parent); self.title("Редактор расследований"); self.geometry("900x680")
        self.manager=manager; self.on_saved=on_saved
        ttk.Label(self,text="РЕДАКТОР РАССЛЕДОВАНИЙ",style="Title.TLabel").pack(pady=12)
        ttk.Label(self,text="Редактируй JSON: дела, улики, варианты ответов, описания и подсказки.").pack(pady=5)
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

class MysteryGameApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_TITLE); self.geometry(WINDOW_SIZE); self.minsize(820,600)
        self.configure(bg="#18212a")
        for folder in (DATA_DIR,ASSETS_DIR,SOUNDS_DIR,SAVES_DIR): folder.mkdir(parents=True,exist_ok=True)
        ensure_default(INVESTIGATIONS_FILE)
        self.data_manager=DataManager(INVESTIGATIONS_FILE)
        try: self.cases=self.data_manager.load_cases()
        except DataError as exc:
            messagebox.showerror("Ошибка данных",str(exc)); self.destroy(); raise
        self.save_manager=SaveManager(SAVES_DIR); self.settings=self.save_manager.load_settings()
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

    def _styles(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except tk.TclError:pass
        scale=float(getattr(self,"settings",{}).get("font_scale",1.0)); s.configure(".",font=("Arial",max(9,int(11*scale))))
        s.configure("Background.TFrame",background="#18212a")
        s.configure("TFrame",background="#202d38")
        s.configure("TLabel",background="#202d38",foreground="#f2eadf")
        s.configure("Title.TLabel",font=("Times New Roman",max(18,int(22*scale)),"bold"),background="#18212a",foreground="#e8c99a")
        s.configure("Hero.TLabel",font=("Times New Roman",max(22,int(30*scale)),"bold"),background="#18212a",foreground="#f2eadf")
        s.configure("Eyebrow.TLabel",font=("Courier New",13,"bold"),background="#18212a",foreground="#c99b68")
        s.configure("Subtitle.TLabel",font=("Georgia",12),background="#18212a",foreground="#c7c0b6")
        s.configure("Footer.TLabel",background="#18212a",foreground="#a9a39a")
        s.configure("Task.TLabel",font=("Georgia",17),background="#202d38",foreground="#fff7e8")
        s.configure("Story.TLabel",font=("Georgia",12),background="#202d38",foreground="#c9c1b6")
        s.configure("Hint.TLabel",background="#202d38",foreground="#e8c99a")
        s.configure("TButton",padding=9,background="#8b6545",foreground="#fff7e8")
        s.map("TButton",background=[("active","#a77c55")])

    def _build_menu(self):
        ttk.Label(self.menu,text="ANASTASIA DAYS",style="Eyebrow.TLabel").pack(pady=(55,8))
        ttk.Label(self.menu,text="MYSTERY FILES",style="Hero.TLabel").pack(pady=(0,12))
        ttk.Label(self.menu,text="Каждая улика приближает к разгадке.",style="Subtitle.TLabel").pack(pady=(0,40))
        box=ttk.Frame(self.menu,style="Background.TFrame"); box.pack()
        self.continue_btn=ttk.Button(box,text="Продолжить расследование",command=self.continue_game)
        self.continue_btn.pack(fill="x",pady=7,ipady=7)
        for label,cmd in (("Новое расследование",self.new_game),("Доска закрытых дел",self.show_board),
                          ("Редактор расследований",self.open_editor),("Настройки",self.open_settings),("Выход",self.on_close)):
            ttk.Button(box,text=label,command=cmd).pack(fill="x",pady=7,ipady=7)
        self.menu_status=ttk.Label(self.menu,text="CASE FILE  •  PRIVATE INVESTIGATION",style="Footer.TLabel"); self.menu_status.pack(side="bottom",pady=8)

    def _build_game(self):
        head=ttk.Frame(self.game,style="Background.TFrame"); head.pack(fill="x")
        self.case_title=ttk.Label(head,text="",style="Eyebrow.TLabel"); self.case_title.pack(side="left")
        ttk.Button(head,text="В меню",command=self.back_to_menu).pack(side="right")
        ttk.Label(self.game,text="ДОСЬЕ РАССЛЕДОВАНИЯ",style="Hero.TLabel").pack(pady=(18,4))
        self.progress=ttk.Label(self.game,text="",style="Subtitle.TLabel"); self.progress.pack(pady=(0,18))
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
        ttk.Label(self.board,text="ДОСКА ЗАКРЫТЫХ ДЕЛ",style="Hero.TLabel").pack(pady=24)
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
            labels="\\n".join(f"{i+1}. {x['name']} — {x.get('case_title',x['case_id'])} — {x.get('updated_at','')[:16]}" for i,x in enumerate(saves))
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
        self.progress.configure(text=f"УЛИКА {i+1} ИЗ {len(case['clues'])}")
        self.task.configure(text=clue["task"]); self.story.configure(text=clue.get("story",""))
        self.answer.set(""); self.hint_label.configure(text="")
        self.inventory_summary.configure(text=f"Найдено предметов: {len(self.active_save.get('inventory',[]))}")
        self.entry.focus_set()

    def submit_answer(self,raw):
        case=self.get_case(); i=self.active_save["current_clue"]; clue=case["clues"][i]
        valid={normalize_answer(x) for x in clue["answers"]}
        normalized = normalize_answer(raw)
        if not normalized or normalized not in valid:return False
        self.active_save.setdefault("inventory",[]).append({"name":clue.get("item_name",f"Улика №{i+1}"),
          "icon":clue.get("icon","🔎"),"description":clue.get("item_description",clue.get("story","")),
          "story":clue.get("story",""),"clue_number":i+1})
        self.active_save["current_clue"]+=1; self.active_save["hints_used"]=0
        if self.active_save["current_clue"]>=len(case["clues"]):self.finish_case()
        else:self.persist()
        return True

    def check_answer(self):
        if not self.answer.get().strip():messagebox.showinfo("Ответ","Сначала введи ответ.",parent=self);return
        if self.submit_answer(self.answer.get()):
            self.audio.effect("clue.wav")
            if self.active_save and not self.active_save.get("completed"):self.refresh_game()
        else:
            self.audio.effect("wrong.wav")
            messagebox.showwarning("Пока неверно","Попробуй другую формулировку или воспользуйся подсказкой.",parent=self)

    def show_hint(self):
        clue=self.get_case()["clues"][self.active_save["current_clue"]]; hints=clue.get("hints",[])
        used=self.active_save.get("hints_used",0); difficulty=self.settings.get("difficulty","normal")
        limit={"easy":len(hints),"normal":min(2,len(hints)),"hard":1}.get(difficulty,2)
        if not hints:self.hint_label.configure(text="Для этой улики подсказок нет.");return
        if used>=limit:self.hint_label.configure(text="Лимит подсказок для выбранной сложности исчерпан.");return
        self.hint_label.configure(text=f"Подсказка {used+1}: {hints[min(used,len(hints)-1)]}")
        self.active_save["hints_used"]=used+1;self.persist()

    def show_inventory(self):InventoryWindow(self,self.active_save.get("inventory",[]))

    def finish_case(self):
        case=self.get_case();self.active_save["completed"]=True
        self.active_save["case_title"]=case["title"];self.active_save["completed_at"]=datetime.now().isoformat(timespec="seconds")
        self.persist();self.audio.effect("success.wav")
        messagebox.showinfo("Дело раскрыто",case.get("final_letter","Дело раскрыто!"),parent=self)
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
    def reload_cases(self):
        try:self.cases=self.data_manager.load_cases()
        except DataError as exc:messagebox.showerror("Ошибка",str(exc),parent=self)
    def on_close(self):
        self.persist();self._stop_menu_animation();self.audio.close();self.destroy()
