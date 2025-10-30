import os
import sys
import glob
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import yaml

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp"]
DEBUG = "-d" in sys.argv or "--debug" in sys.argv


def debug(msg):
    if DEBUG:
        print("[DEBUG]", msg)


def find_images_and_markdowns(folder):
    all_files = glob.glob(os.path.join(folder, "**", "*"), recursive=True)
    images = [f for f in all_files if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
    debug(f"Found {len(images)} image(s): {images}")

    entries = []
    for img_path in sorted(images):
        base, _ = os.path.splitext(img_path)
        md_path = base + ".md"

        if not os.path.exists(md_path):
            md_data = {
                "title": os.path.basename(base),
                "image": os.path.basename(img_path),
                "phototags": [],
                "caption": "",
                "geo": ""
            }
            with open(md_path, "w") as f:
                f.write("---\n")
                yaml.dump(md_data, f)
                f.write("---\n")
            debug(f"Created markdown: {md_path}")
        else:
            debug(f"Found markdown: {md_path}")
            with open(md_path) as f:
                content = f.read()
            try:
                front = content.split("---")[1]
                md_data = yaml.safe_load(front)
                if "geo" not in md_data:
                    md_data["geo"] = ""
            except Exception as e:
                debug(f"Error reading markdown {md_path}: {e}")
                md_data = {"title": os.path.basename(base), "image": os.path.basename(img_path),
                           "phototags": [], "caption": "", "geo": ""}
        entries.append((img_path, md_path, md_data))
    return entries


class PhotoManager(tk.Tk):
    def __init__(self, folder):
        super().__init__()
        self.title("Photo Tag & Caption Manager")
        self.folder = folder
        self.entries = find_images_and_markdowns(folder)
        debug(f"Loaded {len(self.entries)} entries")

        self.selected_indices = set()
        self.default_bg = self.cget("bg")

        self.canvas = tk.Canvas(self, bg="white")
        self.scroll_y = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left")
        tk.Button(btn_frame, text="Clear Selection", command=self.clear_selection).pack(side="left")
        tk.Button(btn_frame, text="Invert Selection", command=self.invert_selection).pack(side="left")
        tk.Button(btn_frame, text="Add Tag", command=self.add_tag).pack(side="left")
        tk.Button(btn_frame, text="Edit Caption", command=self.edit_caption).pack(side="left")
        tk.Button(btn_frame, text="Edit Geo", command=self.edit_geo_bulk).pack(side="left")
        tk.Button(btn_frame, text="Save", command=self.save_all).pack(side="right")

        self.populate()

    def populate(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        self.thumbnails = []
        self.tag_labels = []
        self.geo_entries = []
        for idx, (img_path, _, md) in enumerate(self.entries):
            try:
                debug(f"Opening image: {img_path}")
                im = Image.open(img_path)
                im.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(im)
                debug(f"Thumbnail created for {img_path}")
            except Exception as e:
                debug(f"Error loading {img_path}: {e}")
                continue

            frm = tk.Frame(self.frame, bd=2, relief="groove", padx=2, pady=2)
            frm.grid(row=idx // 3, column=idx % 3, padx=5, pady=5, sticky="nsew")

            lbl = tk.Label(frm, image=photo)
            lbl.image = photo
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, i=idx, f=frm: self.toggle_select(i, f))


            caption_var = tk.StringVar()
            caption_var.set(md["caption"])
            caption_entry = tk.Entry(frm, textvariable=caption_var, width=20, justify="center")
            caption_entry.pack(pady=2)
            caption_entry.bind("<FocusOut>", lambda e, i=idx, v=caption_var: self.update_caption(i, v.get()))

            # Tags
            tags_frame = tk.Frame(frm)
            tags_frame.pack()
            self.tag_labels.append(tags_frame)
            self.refresh_tags(idx)

            # Geo entry
            geo_frame = tk.Frame(frm)
            geo_frame.pack()
            tk.Label(geo_frame, text="Geo:").pack(side="left")
            geo_var = tk.StringVar()
            geo_var.set(md.get("geo", ""))
            geo_entry = tk.Entry(geo_frame, textvariable=geo_var, width=20)
            geo_entry.pack(side="left")
            geo_entry.bind("<FocusOut>", lambda e, i=idx, v=geo_var: self.update_geo(i, v.get()))
            self.geo_entries.append(geo_var)

            self.thumbnails.append(photo)

        self.refresh_selection()

    def refresh_tags(self, idx):
        tags_frame = self.tag_labels[idx]
        for widget in tags_frame.winfo_children():
            widget.destroy()
        md = self.entries[idx][2]
        for tag in md["phototags"]:
            tag_btn = tk.Button(tags_frame, text=f"{tag} ×", relief="solid", bd=1, padx=2, pady=0,
                                command=lambda t=tag, i=idx: self.remove_tag(i, t))
            tag_btn.pack(side="left", padx=1, pady=1)

    def remove_tag(self, idx, tag):
        md = self.entries[idx][2]
        if tag in md["phototags"]:
            md["phototags"].remove(tag)
            self.refresh_tags(idx)

    def toggle_select(self, idx, frame):
        if idx in self.selected_indices:
            self.selected_indices.remove(idx)
            frame.config(bg=self.default_bg)
        else:
            self.selected_indices.add(idx)
            frame.config(bg="lightblue")

    # Selection helpers
    def select_all(self):
        self.selected_indices = set(range(len(self.entries)))
        self.refresh_selection()

    def clear_selection(self):
        self.selected_indices.clear()
        self.refresh_selection()

    def invert_selection(self):
        self.selected_indices = set(range(len(self.entries))) - self.selected_indices
        self.refresh_selection()

    def refresh_selection(self):
        for idx, (img_path, _, md) in enumerate(self.entries):
            try:
                frame = self.frame.grid_slaves(row=idx // 3, column=idx % 3)[0]
                if idx in self.selected_indices:
                    frame.config(bg="lightblue")
                else:
                    frame.config(bg=self.default_bg)
            except IndexError:
                pass

    def add_tag(self):
        if not self.selected_indices:
            messagebox.showinfo("Info", "No photos selected")
            return
        new_tag = simpledialog.askstring("Add Tag", "Enter tag to add:")
        if not new_tag:
            return
        for idx in self.selected_indices:
            md = self.entries[idx][2]
            if new_tag not in md["phototags"]:
                md["phototags"].append(new_tag)
            self.refresh_tags(idx)

    def edit_caption(self):
        if not self.selected_indices:
            messagebox.showinfo("Info", "No photos selected")
            return
        caption = simpledialog.askstring("Edit Caption", "Enter new caption:")
        if caption is None:
            return
        for idx in self.selected_indices:
            self.entries[idx][2]["caption"] = caption
        self.populate()

    def update_geo(self, idx, value):
        self.entries[idx][2]["geo"] = value

    def edit_geo_bulk(self):
        if not self.selected_indices:
            messagebox.showinfo("Info", "No photos selected")
            return
        geo_value = simpledialog.askstring("Edit Geo", "Enter geo coordinates (lat,lon?z=zoom):")
        if geo_value is None:
            return
        for idx in self.selected_indices:
            self.entries[idx][2]["geo"] = geo_value
            self.geo_entries[idx].set(geo_value)

    def update_caption(self, idx, value):
        self.entries[idx][2]["caption"] = value


    def save_all(self):
        for _, md_path, md in self.entries:
            with open(md_path, "w") as f:
                f.write("---\n")
                yaml.dump(md, f)
                f.write("---\n")
        messagebox.showinfo("Saved", "Markdown files updated!")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Choose photo directory")
    root.destroy()
    if folder:
        debug(f"Selected folder: {folder}")
        app = PhotoManager(folder)
        app.mainloop()
    else:
        debug("No folder selected")

