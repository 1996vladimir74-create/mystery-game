import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from datetime import datetime
from pathlib import Path
import shutil
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
        super().__init__(parent); self.title("Настройки"); self.geometry("460x520")
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
    IMAGE_FIELDS = {
        "Обложка расследования": ("case", "cover_image"),
        "Фон расследования": ("case", "background_image"),
        "Документ расследования": ("case", "document_image"),
        "Фон отдельной улики / этапа": ("clue", "background_image"),
        "Иллюстрация улики": ("clue", "illustration_image"),
        "Документ или фото улики": ("clue", "document_image"),
        "Изображение найденного предмета": ("clue", "item_image"),
    }

    def __init__(self,parent,manager,on_saved):
        super().__init__(parent); self.title("Редактор расследований"); self.geometry("980x760")
        self.manager=manager; self.on_saved=on_saved
        ttk.Label(self,text="РЕДАКТОР РАССЛЕДОВАНИЙ",style="Title.TLabel").pack(pady=10)
        ttk.Label(self,text="У каждого расследования и каждой улики могут быть собственные тексты и изображения. "
                            "Выбери дело, этап и тип изображения, затем добавь файл с компьютера.",
                  wraplength=900).pack(pady=4)
        try: cases=manager.load_cases()
        except DataError as exc:
            messagebox.showerror("Ошибка данных",str(exc),parent=self); cases=[]
        toolbar=ttk.LabelFrame(self,text="Добавить изображение",padding=10)
        toolbar.pack(fill="x",padx=14,pady=8)
        self.case_var=tk.StringVar(value=cases[0].get("title","") if cases else "")
        self.case_combo=ttk.Combobox(toolbar,textvariable=self.case_var,
            values=[case.get("title","") for case in cases],state="readonly",width=28)
        self.case_combo.grid(row=0,column=0,padx=5,pady=4,sticky="ew")
        self.clue_var=tk.StringVar(value="Улика №1")
        self.clue_combo=ttk.Combobox(toolbar,textvariable=self.clue_var,
            values=[f"Улика №{i+1}" for i in range(len(cases[0].get("clues",[])))] if cases else [],
            state="readonly",width=14)
        self.clue_combo.grid(row=0,column=1,padx=5,pady=4)
        self.slot_var=tk.StringVar(value="Иллюстрация улики")
        self.slot_combo=ttk.Combobox(toolbar,textvariable=self.slot_var,
            values=list(self.IMAGE_FIELDS),state="readonly",width=34)
        self.slot_combo.grid(row=0,column=2,padx=5,pady=4)
        ttk.Button(toolbar,text="Выбрать файл изображения…",command=self.assign_image).grid(row=0,column=3,padx=6,pady=4)
        toolbar.columnconfigure(0,weight=1)
        self.case_combo.bind("<<ComboboxSelected>>",self.update_clue_choices)
        ttk.Label(self,text="Тексты, ответы, подсказки и дополнительные настройки этапов редактируются в JSON ниже:").pack(anchor="w",padx=16)
        self.text=tk.Text(self,wrap="none",font=("Consolas",10),bg="#101820",fg="#f2eadf",
                          insertbackground="white",undo=True)
        self.text.pack(fill="both",expand=True,padx=16,pady=8)
        self.text.insert("1.0",json.dumps(cases,ensure_ascii=False,indent=2))
        ttk.Button(self,text="Проверить и сохранить расследования",command=self.save).pack(pady=12)

    def update_clue_choices(self,_event=None):
        try:
            cases=json.loads(self.text.get("1.0","end-1c"))
            index=next(i for i,c in enumerate(cases) if c.get("title")==self.case_var.get())
            clues=cases[index].get("clues",[])
            self.clue_combo.configure(values=[f"Улика №{i+1}" for i in range(len(clues))])
            self.clue_var.set("Улика №1" if clues else "")
        except (ValueError,StopIteration,TypeError,json.JSONDecodeError):
            self.clue_combo.configure(values=[]); self.clue_var.set("")

    def assign_image(self):
        source=filedialog.askopenfilename(parent=self,title="Выбери изображение",
            filetypes=[("Изображения","*.png *.jpg *.jpeg *.webp *.bmp *.gif"),("Все файлы","*.*")])
        if not source:return
        try:
            cases=json.loads(self.text.get("1.0","end-1c"))
            case_index=next(i for i,c in enumerate(cases) if c.get("title")==self.case_var.get())
            target,field=self.IMAGE_FIELDS[self.slot_var.get()]
            if target=="case":
                destination=cases[case_index]
            else:
                clue_index=int(self.clue_var.get().split("№")[-1])-1
                destination=cases[case_index]["clues"][clue_index]
            image_dir=ASSETS_DIR/"images"/"custom"
            image_dir.mkdir(parents=True,exist_ok=True)
            source_path=Path(source)
            filename=datetime.now().strftime("%Y%m%d_%H%M%S_%f")+"_"+source_path.name
            target_path=image_dir/filename
            shutil.copy2(source_path,target_path)
            destination[field]=f"custom/{filename}"
            self.text.delete("1.0","end")
            self.text.insert("1.0",json.dumps(cases,ensure_ascii=False,indent=2))
            messagebox.showinfo("Изображение добавлено",
                f"Файл скопирован в assets/images/custom/\nПоле {field} обновлено.\nНажми «Проверить и сохранить расследования».",
                parent=self)
        except (OSError,ValueError,KeyError,StopIteration,IndexError,json.JSONDecodeError) as exc:
            messagebox.showerror("Не удалось добавить изображение",str(exc),parent=self)

    def save(self):
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
            "id":"dlc-"+datetime.now().strftime("%Y%m%d%H%M%S%f"),
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
        self.menu=ttk.Frame(root,style="Background.TFrame",padding=0)
        self.game=ttk.Frame(root,style="Background.TFrame",padding=28)
        self.board=ttk.Frame(root,style="Background.TFrame",padding=28)
        self.case_intro=ttk.Frame(root,style="Background.TFrame",padding=28)
        for frame in (self.menu,self.game,self.board,self.case_intro): frame.grid(row=0,column=0,sticky="nsew")
        self._build_menu(); self._build_game(); self._build_board(); self._build_case_intro()
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
        # Reuse the original detective-desk image as the full-screen menu background.
        self.menu_canvas=tk.Canvas(self.menu,bg="#30251d",highlightthickness=0)
        self.menu_canvas.place(relx=0,rely=0,relwidth=1,relheight=1)
        self.menu_background_photo=self.image_assets.load_fit(
            "branding/menu-background.jpg",(1100,760),centering=(0.5,0.5))
        if self.menu_background_photo:
            self.menu_canvas.create_image(500,350,image=self.menu_background_photo,anchor="center")
        else:
            self.menu_canvas.create_rectangle(0,0,1000,700,fill="#38291f",outline="")
        self.menu_canvas.create_rectangle(28,22,700,100,fill="#2c211b",outline="#b08a5c",width=2)
        self.menu_canvas.create_text(365,48,text="ANASTASIA DAYS",fill="#f0d5a7",font=("Georgia",25,"bold"))
        self.menu_canvas.create_text(365,78,text="ЧАСТНОЕ ДЕТЕКТИВНОЕ АГЕНТСТВО  •  АРХИВ ДЕЛ",
                                     fill="#c5a77d",font=("Courier New",9,"bold"))
        self.menu_canvas.create_rectangle(28,118,700,652,fill="#26352e",outline="#b08a5c",width=2)
        self.menu_canvas.create_text(364,140,text="АКТИВНЫЕ РАССЛЕДОВАНИЯ",
                                     fill="#ead6b8",font=("Courier New",13,"bold"))
        self.dlc_cards=tk.Frame(self.menu_canvas,bg="#26352e")
        self.menu_canvas.create_window(364,390,window=self.dlc_cards,width=620,height=470)
        self.active_dlc_title=tk.Label(self.menu_canvas,text="Выбери папку с делом",bg="#26352e",fg="#f0d5a7",
            font=("Georgia",12,"italic"),wraplength=600,justify="center")
        self.menu_canvas.create_window(364,166,window=self.active_dlc_title)
        self.menu_canvas.create_rectangle(725,118,972,652,fill="#30231c",outline="#b08a5c",width=2)
        self.menu_canvas.create_text(848,150,text="МЕНЮ",fill="#f0d5a7",font=("Georgia",17,"bold"))
        self.menu_actions=tk.Frame(self.menu_canvas,bg="#30231c")
        self.menu_canvas.create_window(848,390,window=self.menu_actions,width=220,height=410)
        for label,cmd in (("ЗАГРУЗКА",self.continue_game),("ОПЦИИ",self.open_settings),
                          ("ДОСКА РАСКРЫТЫХ ДЕЛ",self.show_board),("ВЫХОД",self.on_close)):
            tk.Button(self.menu_actions,text=label,command=cmd,relief="raised",bd=2,
                bg="#e4d3b5",fg="#493426",activebackground="#f5e8d2",
                font=("Georgia",10,"bold"),padx=10,pady=12,cursor="hand2",
                wraplength=190).pack(fill="x",padx=6,pady=10)
        self._populate_dlc_list()

    def _populate_dlc_list(self):
        for child in self.dlc_cards.winfo_children(): child.destroy()
        if not self.dlcs:
            tk.Label(self.dlc_cards,text="Пока нет заведённых дел",bg="#26352e",fg="#ead6b8",
                     font=("Georgia",14)).pack(pady=30)
            return
        for index,dlc in enumerate(self.dlcs):
            card=tk.Frame(self.dlc_cards,bg="#e8dcc5",highlightthickness=3,
                          highlightbackground="#c6a879" if index==0 else "#765b43",bd=1)
            card.pack(side="left",fill="y",expand=True,padx=9,pady=10,ipadx=10,ipady=8)
            tk.Label(card,text="▤  ПАПКА ДЕЛА",bg="#e8dcc5",fg="#6d5038",
                     font=("Courier New",9,"bold")).pack(pady=(8,12))
            tk.Label(card,text=dlc["title"],bg="#e8dcc5",fg="#34271e",
                     font=("Georgia",12,"bold"),wraplength=190,justify="center").pack(padx=10,pady=8)
            if index==0:
                tk.Label(card,text="НОВОЕ ДЕЛО",bg="#9d493d",fg="#fff1df",
                         font=("Courier New",8,"bold"),padx=7,pady=3).pack(pady=4)
            tk.Label(card,text=dlc.get("description",""),bg="#e8dcc5",fg="#6b5b4b",
                     font=("Georgia",9),wraplength=185,justify="center").pack(padx=8,pady=6)
            tk.Button(card,text="ОТКРЫТЬ ДЕЛО",command=lambda item=dlc:self._on_dlc_selected(item),
                bg="#76543a",fg="#fff5e7",activebackground="#a77c55",relief="raised",
                font=("Georgia",9,"bold"),cursor="hand2").pack(pady=(12,8))

    def _on_dlc_selected(self,dlc):
        self.active_dlc_title.configure(text=dlc["title"])
        if messagebox.askyesno("Начать DLC",f"Начать историю «{dlc['title']}»?\\n\\nКвесты будут проходиться последовательно.",parent=self):
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
        self.active_save["intro_pending"]=True
        self.persist()
        self.show("intro")

    def _build_case_intro(self):
        top=ttk.Frame(self.case_intro,style="Background.TFrame"); top.pack(fill="x")
        ttk.Button(top,text="← В меню",command=self.back_to_menu).pack(side="left")
        ttk.Label(self.case_intro,text="НОВОЕ ДЕЛО / CASE BRIEFING",style="Eyebrow.TLabel").pack(pady=(35,10))
        self.intro_title=ttk.Label(self.case_intro,text="",style="Hero.TLabel",wraplength=850)
        self.intro_title.pack(pady=8)
        self.intro_image=ttk.Label(self.case_intro,style="Background.TFrame")
        self.intro_image.pack(pady=12)
        self.intro_description=ttk.Label(self.case_intro,text="",style="Story.TLabel",wraplength=760,
                                         justify="center")
        self.intro_description.pack(padx=60,pady=20)
        self.intro_meta=ttk.Label(self.case_intro,text="",style="Subtitle.TLabel")
        self.intro_meta.pack(pady=8)
        ttk.Button(self.case_intro,text="НАЧАТЬ РАССЛЕДОВАНИЕ",command=self.begin_case).pack(pady=20)

    def refresh_case_intro(self):
        case=self.get_case()
        self.intro_title.configure(text=case["title"])
        self.intro_description.configure(text=case.get("description","Материалы дела ожидают изучения."))
        self.intro_meta.configure(text=f"ДЕЛО {self.active_save.get('quest_ids',[case['id']]).index(case['id'])+1} ИЗ {len(self.active_save.get('quest_ids',[case['id']]))}")
        image_path=case.get("cover_image") or case.get("illustration_image") or case.get("background_image")
        photo=self.image_assets.load_fit(image_path,(650,300),centering=(0.5,0.5)) if image_path else None
        self.intro_image.configure(image=photo if photo else "",text="" if photo else "ФОТОГРАФИЯ / ОБЛОЖКА ДЕЛА")
        self.intro_image.image=photo

    def begin_case(self):
        self.active_save["intro_pending"]=False
        self.persist()
        self.show("game")

    def _build_game(self):
        self.case_background=tk.Label(self.game,borderwidth=0,bg=self.theme.get("colors",{}).get("window","#18212a"))
        self.case_background.place(relx=0,rely=0,relwidth=1,relheight=1); self.case_background.lower()
        head=ttk.Frame(self.game,style="Background.TFrame"); head.pack(fill="x")
        self.case_title=ttk.Label(head,text="",style="Eyebrow.TLabel"); self.case_title.pack(side="left")
        ttk.Button(head,text="В меню",command=self.back_to_menu).pack(side="right",padx=(8,0))
        ttk.Button(head,text="Блокнот",command=self.show_notebook).pack(side="right",padx=5)
        ttk.Button(head,text="Материалы",command=self.show_inventory).pack(side="right",padx=5)
        ttk.Label(self.game,text="ДОСЬЕ РАССЛЕДОВАНИЯ",style="Hero.TLabel").pack(pady=(18,4))
        self.progress=ttk.Label(self.game,text="",style="Subtitle.TLabel"); self.progress.pack(pady=(0,10))
        self.case_art=ttk.Label(self.game,style="Background.TFrame"); self.case_art.pack(pady=(0,8))
        media=ttk.Frame(self.game,style="Background.TFrame"); media.pack(fill="x",padx=24,pady=(0,8))
        self.clue_art=ttk.Label(media,style="Background.TFrame",cursor="hand2")
        self.clue_art.pack(side="left",expand=True,padx=5)
        self.clue_art.bind("<Button-1>",lambda _e:self.open_evidence_viewer("illustration_image"))
        self.document_art=ttk.Label(media,style="Background.TFrame",cursor="hand2")
        self.document_art.pack(side="left",expand=True,padx=5)
        self.document_art.bind("<Button-1>",lambda _e:self.open_evidence_viewer("document_image"))
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
        board_scroll=ttk.Scrollbar(self.board,orient="vertical",command=self.board_canvas.yview)
        self.board_canvas.configure(yscrollcommand=board_scroll.set)
        board_scroll.pack(side="right",fill="y",padx=(0,10),pady=10)
        self.board_canvas.pack(side="left",fill="both",expand=True,padx=10,pady=10)

    def show(self,name):
        {"menu":self.menu,"game":self.game,"board":self.board,"intro":self.case_intro}[name].tkraise()
        if name=="menu":
            self._start_menu_animation()
        else: self._stop_menu_animation()
        if name=="game" and self.active_save:self.refresh_game()
        if name=="intro" and self.active_save:self.refresh_case_intro()
        if name=="board":self.refresh_board()

    def _start_menu_animation(self):
        self._stop_menu_animation()
        if self.settings.get("animations", True): self._animate_menu()
    def _animate_menu(self):
        if not self.winfo_exists() or not self.settings.get("animations", True): return
        self._animation_phase = not self._animation_phase
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
        saves=self.save_manager.list_saves()
        if not saves:
            messagebox.showinfo("Сохранения","Сохранений пока нет.",parent=self)
            return
        window=tk.Toplevel(self); window.title("Сохранения расследований"); window.geometry("700x470")
        window.configure(bg="#e8dcc5"); window.transient(self)
        tk.Label(window,text="АРХИВ СОХРАНЕНИЙ",bg="#e8dcc5",fg="#493426",
                 font=("Courier New",15,"bold")).pack(pady=14)
        listing=tk.Listbox(window,font=("Georgia",11),bg="#f4eddf",fg="#34271e",
                           selectbackground="#8b6545",height=13)
        listing.pack(fill="both",expand=True,padx=18,pady=8)
        def refresh():
            listing.delete(0,"end")
            current=self.save_manager.list_saves()
            for item in current:
                status="ЗАВЕРШЕНО" if item.get("completed") else "В ПРОЦЕССЕ"
                title=item.get("case_title",item.get("dlc_title",item.get("case_id","Дело")))
                listing.insert("end",f"{item.get('name','Без названия')}  —  {title}  —  {status}  —  {item.get('updated_at','')[:16]}")
        refresh()
        buttons=tk.Frame(window,bg="#e8dcc5"); buttons.pack(fill="x",padx=18,pady=12)
        def selected_save():
            selection=listing.curselection()
            if not selection:return None
            values=self.save_manager.list_saves()
            return values[selection[0]] if selection[0]<len(values) else None
        def load_selected():
            item=selected_save()
            if not item:
                messagebox.showwarning("Выбор сохранения","Сначала выбери сохранение.",parent=window); return
            if item.get("completed"):
                messagebox.showinfo("История завершена","Это сохранение уже завершено. Его можно удалить, но продолжить нельзя.",parent=window); return
            try:
                self.active_save=self.save_manager.load(item["id"])
                self.get_case()
                window.destroy()
                if self.active_save.get("intro_pending",False): self.show("intro")
                else: self.show("game")
            except SaveError as exc:
                messagebox.showerror("Ошибка сохранения",str(exc),parent=window)
        def delete_selected():
            item=selected_save()
            if not item:
                messagebox.showwarning("Удаление","Сначала выбери сохранение.",parent=window); return
            if not messagebox.askyesno("Удалить сохранение",
                f"Удалить «{item.get('name','Без названия')}»?\nЭто действие нельзя отменить.",parent=window):
                return
            try:
                self.save_manager.delete(item["id"])
                if self.active_save and self.active_save.get("id")==item["id"]:
                    self.active_save=None
                refresh()
                messagebox.showinfo("Удалено","Сохранение удалено.",parent=window)
                self.refresh_board()
            except SaveError as exc:
                messagebox.showerror("Ошибка удаления",str(exc),parent=window)
        tk.Button(buttons,text="Загрузить",command=load_selected,bg="#76543a",fg="white",
                  font=("Georgia",10,"bold"),padx=16,pady=8).pack(side="left",padx=5)
        tk.Button(buttons,text="Удалить выбранное",command=delete_selected,bg="#9d493d",fg="white",
                  font=("Georgia",10,"bold"),padx=16,pady=8).pack(side="left",padx=5)
        tk.Button(buttons,text="Закрыть",command=window.destroy,bg="#d7c6a8",
                  font=("Georgia",10,"bold"),padx=16,pady=8).pack(side="right",padx=5)

    def refresh_game(self):
        case=self.get_case(); i=self.active_save["current_clue"]
        if i>=len(case["clues"]): self.finish_case(); return
        clue=case["clues"][i]; self.case_title.configure(text=case["title"])
        self._display_image(self.case_background,clue.get("background_image") or case.get("background_image"),(1000,700),"case_background")
        self._display_image(self.case_art,case.get("cover_image"),(720,90),"case_art")
        self._display_image(self.clue_art,clue.get("illustration_image"),(300,120),"clue_art")
        self._display_image(self.document_art,clue.get("document_image") or case.get("document_image"),(300,120),"document_art")
        quest_ids=self.active_save.get("quest_ids",[case["id"]])
        try: quest_number=quest_ids.index(case["id"])+1
        except ValueError: quest_number=1
        self.progress.configure(text=f"РАССЛЕДОВАНИЕ {quest_number} ИЗ {len(quest_ids)}   •   УЛИКА {i+1} ИЗ {len(case['clues'])}")
        self.task.configure(text=clue["task"]); self.story.configure(text=clue.get("story",""))
        self.answer.set(""); self.hint_label.configure(text="")
        self.inventory_summary.configure(text=f"Найдено предметов: {len(self.active_save.get('inventory',[]))}")
        self.entry.focus_set()

    def open_evidence_viewer(self, field):
        case=self.get_case(); clue=case["clues"][self.active_save["current_clue"]]
        path=clue.get(field) or (case.get("document_image") if field=="document_image" else None)
        photo=self.image_assets.load(path,(900,650)) if path else None
        window=tk.Toplevel(self); window.title("Материалы дела — просмотр")
        window.configure(bg="#201b17"); window.geometry("940x720")
        label=tk.Label(window,image=photo,bg="#201b17",fg="#ead6b8",
                       text="Изображение для этой улики пока не добавлено." if photo is None else "")
        label.image=photo; label.pack(fill="both",expand=True,padx=15,pady=15)
        tk.Button(window,text="Закрыть",command=window.destroy,bg="#e4d3b5").pack(pady=10)

    def _display_image(self, widget, relative_path, size, ref_name):
        photo=self.image_assets.load(relative_path,size) if relative_path else None
        setattr(self,ref_name+"_photo",photo)
        placeholders={"case_art":"ОБЛОЖКА ДЕЛА — добавь cover_image","clue_art":"ИЛЛЮСТРАЦИЯ УЛИКИ — добавь illustration_image","document_art":"ФОТО / ДОКУМЕНТ — добавь document_image"}
        widget.configure(image=photo if photo else "",text="" if photo else placeholders.get(ref_name,""))

    def show_discovery(self, clue, discovery):
        window=tk.Toplevel(self); window.title("Новая находка"); window.geometry("720x620")
        window.configure(bg="#e8dcc5"); window.transient(self)
        tk.Label(window,text="УЛИКА ДОБАВЛЕНА В ДОСЬЕ",bg="#e8dcc5",fg="#493426",
                 font=("Courier New",15,"bold")).pack(pady=14)
        path=clue.get("item_image")
        photo=self.image_assets.load(path,(620,360)) if path else None
        image_label=tk.Label(window,image=photo,bg="#e8dcc5",fg="#493426",
            text="Изображение найденного предмета не добавлено." if photo is None else "",
            font=("Georgia",11))
        image_label.image=photo; image_label.pack(fill="both",expand=True,padx=18,pady=8)
        tk.Label(window,text=clue.get("item_name","Найденный предмет"),bg="#e8dcc5",fg="#493426",
                 font=("Georgia",14,"bold")).pack(pady=5)
        tk.Label(window,text=discovery,bg="#e8dcc5",fg="#493426",wraplength=650,
                 justify="center",font=("Georgia",11)).pack(padx=22,pady=8)
        tk.Button(window,text="Продолжить расследование",command=window.destroy,
                  bg="#76543a",fg="white",font=("Georgia",10,"bold"),padx=18,pady=9).pack(pady=14)
        window.grab_set()
        self.wait_window(window)

    def submit_answer(self,raw):
        case=self.get_case(); i=self.active_save["current_clue"]; clue=case["clues"][i]
        valid={normalize_answer(x) for x in clue["answers"]}
        normalized = normalize_answer(raw)
        if not normalized or normalized not in valid:return False
        self.active_save.setdefault("inventory",[]).append({"name":clue.get("item_name",f"Улика №{i+1}"),
          "icon":clue.get("icon","🔎"),"description":clue.get("item_description",clue.get("story","")),
          "story":clue.get("story",""),"item_image":clue.get("item_image"),"clue_number":i+1,
          "case_id":self.active_save.get("case_id")})
        self.active_save["current_clue"]+=1; self.active_save["hints_used"]=0
        self.persist()
        return True

    def check_answer(self):
        if not self.answer.get().strip():
            messagebox.showinfo("Ответ", "Сначала введи ответ.", parent=self)
            return
        clue_index = self.active_save["current_clue"]
        original_case_id = self.active_save.get("case_id")
        clue = self.get_case()["clues"][clue_index]
        if self.submit_answer(self.answer.get()):
            self.audio.effect("clue.wav")
            discovery = clue.get("discovery_message") or (
                f"Улика «{clue.get('item_name', 'Найденный предмет')}» добавлена в инвентарь.\n\n"
                f"{clue.get('story', 'Расследование продолжается.')}"
            )
            self.show_discovery(clue, discovery)
            if self.active_save and self.active_save.get("case_id")==original_case_id:
                if self.active_save["current_clue"] >= len(self.get_case()["clues"]):
                    self.finish_case()
                else:
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

    def show_notebook(self):
        window=tk.Toplevel(self); window.title("Блокнот расследования"); window.geometry("620x560")
        window.configure(bg="#e8dcc5")
        tk.Label(window,text="ЗАМЕТКИ ДЕТЕКТИВА",bg="#e8dcc5",fg="#493426",
                 font=("Courier New",16,"bold")).pack(pady=16)
        body=tk.Text(window,wrap="word",font=("Georgia",11),bg="#f4eddf",fg="#34271e",
                     relief="flat",padx=18,pady=14)
        body.pack(fill="both",expand=True,padx=18,pady=10)
        case=self.get_case()
        body.insert("end",f"ДЕЛО: {case['title']}\\n")
        body.insert("end",f"ИСТОРИЯ: {self.active_save.get('dlc_title',case['title'])}\\n\\n")
        body.insert("end","НАЙДЕННЫЕ МАТЕРИАЛЫ\\n"+"—"*32+"\\n")
        inventory=self.active_save.get("inventory",[])
        if not inventory: body.insert("end","Пока нет собранных улик.\\n")
        for item in inventory:
            body.insert("end",f"\\n{item.get('icon','•')} {item.get('name','Улика')}\\n")
            body.insert("end",f"{item.get('description','')}\\n{item.get('story','')}\\n")
        body.configure(state="disabled")
        tk.Button(window,text="Закрыть блокнот",command=window.destroy,bg="#76543a",fg="white").pack(pady=12)

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
            self.active_save["intro_pending"]=True
            self.persist()
            self.show("intro")
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
        self.board_canvas.delete("all")
        self.board_canvas.configure(bg="#76543a")
        self.board_canvas.create_text(500,24,text="ДОСКА РАСКРЫТЫХ ДЕЛ / СВЯЗИ УЛИК",
                                      fill="#fff0d8",font=("Courier New",15,"bold"))
        completed=self.save_manager.completed_cases()
        if not completed:
            self.board_canvas.create_text(500,180,text="Пока нет закрытых дел. Первое расследование ждёт тебя!",
                                          fill="#fff0d8",font=("Georgia",14))
            self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all"))
            return
        saves=[item for item in self.save_manager.list_saves() if item.get("completed")]
        evidence_by_case={}
        for save in saves:
            ids=save.get("completed_case_ids") or [save.get("case_id")]
            for case_id in ids:
                evidence_by_case.setdefault(case_id,[])
                for evidence in save.get("inventory",[]):
                    if evidence.get("case_id", case_id)==case_id and evidence not in evidence_by_case[case_id]:
                        evidence_by_case[case_id].append(evidence)

        # One dossier per row; evidence is laid out in three columns with no item limit.
        y=100
        x_positions=[190,500,810]
        for item in completed:
            evidence=evidence_by_case.get(item["case_id"],[])
            rows=max(1,(len(evidence)+2)//3)
            self.board_canvas.create_rectangle(365,y-42,635,y+42,fill="#eadfc9",outline="#3e2c20",width=2)
            self.board_canvas.create_text(500,y-17,text="ДЕЛО РАСКРЫТО",fill="#8b493d",font=("Courier New",9,"bold"))
            self.board_canvas.create_text(500,y+10,text=item["name"],fill="#34271e",
                                          font=("Georgia",10,"bold"),width=245,justify="center")
            for n,entry in enumerate(evidence):
                ex=x_positions[n%3]
                ey=y+105+(n//3)*58
                self.board_canvas.create_line(500,y+42,ex,ey-19,fill="#e1c18e",width=2)
                self.board_canvas.create_oval(ex-7,ey-7,ex+7,ey+7,fill="#a64e43",outline="#f3e4c9")
                self.board_canvas.create_rectangle(ex-86,ey-16,ex+86,ey+17,fill="#f2e7d3",outline="#70563d")
                self.board_canvas.create_text(ex,ey,text=entry.get("name","Улика"),fill="#34271e",
                                              font=("Georgia",9),width=160)
            footer_y=y+105+(rows-1)*58+42
            self.board_canvas.create_text(500,footer_y,
                text=f"Найдено улик: {len(evidence)}   •   Закрыто: {item.get('completed_at','')[:10]}",
                fill="#fff0d8",font=("Georgia",8))
            y=footer_y+85
        self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all"))

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
