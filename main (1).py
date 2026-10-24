# ======================================================================
# Student Study Material Management System  (Version 2)
# Features:
#   * Login system with two roles: ADMIN and USER
#   * Only the admin can upload (add) PDF / PPT files and delete them
#   * Students register, then wait for the admin to GRANT ACCESS
#   * Approved students can view, search and open the materials
# Data is stored in plain text files (no database, no JSON):
#   study_materials.txt  -> material records
#   users.txt            -> user accounts
#   uploads/             -> folder holding the uploaded PDF / PPT files
# ======================================================================

# ----------------------------------------------------------------------
# 1. IMPORT REQUIRED LIBRARIES (all built into Python)
# ----------------------------------------------------------------------
import os                                   # file paths, delete files
import sys                                  # to find the operating system
import shutil                               # to copy uploaded files
import hashlib                              # to protect passwords
import subprocess                           # to open files on Mac / Linux
import tkinter as tk                        # main GUI library
from tkinter import ttk, messagebox, filedialog

# ----------------------------------------------------------------------
# 2. INITIALIZE THE MAIN WINDOW AND SETTINGS
# ----------------------------------------------------------------------
root = tk.Tk()
root.title("Student Study Material Management System")
root.geometry("1200x780")
root.minsize(1050, 700)

# Colour palette (dark blue, white, light grey)
DARK_BLUE = "#1F3A5F"
MID_BLUE = "#2E5C8A"
LIGHT_GREY = "#F2F4F7"
WHITE = "#FFFFFF"
RED = "#B03A2E"
GREEN = "#2E7D32"

# Default admin account (created automatically the first time)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# All files are kept in the same folder as this program
try:
    FOLDER = os.path.dirname(os.path.abspath(__file__))
except NameError:
    FOLDER = os.getcwd()
FILE_NAME = os.path.join(FOLDER, "study_materials.txt")
USERS_FILE = os.path.join(FOLDER, "users.txt")
UPLOAD_FOLDER = os.path.join(FOLDER, "uploads")

SEPARATOR = "|"                             # separates fields in one record
ALLOWED_EXTENSIONS = [".pdf", ".ppt", ".pptx"]

# ----------------------------------------------------------------------
# 3. CREATE THE LIST AND DICTIONARY STRUCTURES
# ----------------------------------------------------------------------
# 'materials' is a LIST of DICTIONARIES, for example:
# {"id": "M001", "title": "...", "subject": "...", "module": "1",
#  "type": "PDF", "path": "M001_notes.pdf", "description": "..."}
materials = []
FIELD_NAMES = ["id", "title", "subject", "module", "type", "path", "description"]
MATERIAL_TYPES = ["Notes", "PDF", "Assignment", "Question Paper",
                  "Reference Material", "Other"]

# 'users' is a LIST of DICTIONARIES, for example:
# {"username": "ravi", "password": "<hash>", "role": "user", "status": "pending"}
# status can be: pending (waiting), approved (has access), revoked (blocked)
users = []
USER_FIELDS = ["username", "password", "role", "status"]

# Dictionary that remembers who is logged in right now
current_user = {}


# ----------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------
def clean_text(text):
    """Make user text safe to store: remove the separator and new lines."""
    text = text.replace(SEPARATOR, "/")
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    return text.strip()


def hash_password(password):
    """Turn a password into a scrambled string so it is not stored as plain text."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_id():
    """Create a unique ID like M001, M002 ... that is not already used."""
    number = len(materials) + 1
    while True:
        new_id = "M" + str(number).zfill(3)
        if not id_exists(new_id):
            return new_id
        number = number + 1


def id_exists(material_id):
    """Return True if the Material ID is already in the list."""
    for item in materials:
        if item["id"].lower() == material_id.lower():
            return True
    return False


def find_material(material_id):
    """Return the material dictionary with this ID (or None)."""
    for item in materials:
        if item["id"].lower() == material_id.lower():
            return item
    return None


def find_user(username):
    """Return the user dictionary with this username (or None)."""
    for person in users:
        if person["username"].lower() == username.lower():
            return person
    return None


def is_valid_id(material_id):
    """An ID may only contain letters, digits, '-' and '_' (safe for file names)."""
    for ch in material_id:
        if not (ch.isalnum() or ch == "-" or ch == "_"):
            return False
    return True


# ----------------------------------------------------------------------
# 4. FILE HANDLING - USERS
# ----------------------------------------------------------------------
def save_users():
    """Rewrite users.txt from the 'users' list."""
    try:
        with open(USERS_FILE, "w") as file:
            for person in users:
                values = []
                for name in USER_FIELDS:
                    values.append(person[name])
                file.write(SEPARATOR.join(values) + "\n")
        return True
    except OSError:
        messagebox.showerror("File Error", "Could not save the users file.")
        return False


def load_users():
    """Read users.txt into the 'users' list. Create the admin if file is new."""
    users.clear()
    try:
        with open(USERS_FILE, "r") as file:
            for line in file:
                line = line.strip()
                if line == "":
                    continue
                parts = line.split(SEPARATOR)
                if len(parts) == len(USER_FIELDS):
                    person = {}
                    for i in range(len(USER_FIELDS)):
                        person[USER_FIELDS[i]] = parts[i]
                    users.append(person)
    except FileNotFoundError:
        # First run: create the file with the default admin account
        users.append({"username": ADMIN_USERNAME,
                      "password": hash_password(ADMIN_PASSWORD),
                      "role": "admin", "status": "approved"})
        save_users()
    except OSError:
        messagebox.showerror("File Error", "Could not read the users file.")


# ----------------------------------------------------------------------
# 4. FILE HANDLING - MATERIALS
# ----------------------------------------------------------------------
def load_materials():
    """Read all records from the text file into the 'materials' list."""
    materials.clear()
    try:
        with open(FILE_NAME, "r") as file:
            for line in file:
                line = line.strip()
                if line == "":
                    continue
                parts = line.split(SEPARATOR)
                if len(parts) == len(FIELD_NAMES):
                    record = {}
                    for i in range(len(FIELD_NAMES)):
                        record[FIELD_NAMES[i]] = parts[i]
                    materials.append(record)
    except FileNotFoundError:
        try:
            with open(FILE_NAME, "w") as file:
                file.write("")
        except OSError:
            messagebox.showerror("File Error", "Could not create the data file.")
    except OSError:
        messagebox.showerror("File Error", "Could not read the data file.")


def save_materials():
    """Rewrite the whole text file from the list (used after deleting)."""
    try:
        with open(FILE_NAME, "w") as file:
            for item in materials:
                values = []
                for name in FIELD_NAMES:
                    values.append(item[name])
                file.write(SEPARATOR.join(values) + "\n")
        return True
    except OSError:
        messagebox.showerror("File Error", "Could not save the data file.")
        return False


def append_material_to_file(item):
    """Add ONE new record at the end of the text file."""
    try:
        with open(FILE_NAME, "a") as file:
            values = []
            for name in FIELD_NAMES:
                values.append(item[name])
            file.write(SEPARATOR.join(values) + "\n")
        return True
    except OSError:
        messagebox.showerror("File Error", "Could not write to the data file.")
        return False


def create_upload_folder():
    """Make sure the 'uploads' folder exists."""
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except OSError:
        messagebox.showerror("Folder Error", "Could not create the uploads folder.")


# ----------------------------------------------------------------------
# SCREEN HELPERS
# ----------------------------------------------------------------------
def clear_screen():
    """Remove everything from the area under the header."""
    for widget in screen.winfo_children():
        widget.destroy()


def has_access():
    """Re-check the user file: has the admin revoked this user's access?"""
    load_users()
    person = find_user(current_user["username"])
    if person is None or (person["role"] != "admin" and person["status"] != "approved"):
        messagebox.showwarning("Access Removed",
                               "Your access has been removed by the admin.")
        logout()
        return False
    return True


def is_admin():
    """Return True when the logged-in person is the admin."""
    return current_user.get("role") == "admin"


# ----------------------------------------------------------------------
# 5. LOGIN, REGISTER AND LOGOUT
# ----------------------------------------------------------------------
def login():
    """Check username and password, then open the main screen."""
    username = username_entry.get().strip()
    password = password_entry.get()

    if username == "" or password == "":
        messagebox.showwarning("Missing Information",
                               "Please enter username and password.")
        return

    load_users()
    person = find_user(username)
    if person is None or person["password"] != hash_password(password):
        messagebox.showerror("Login Failed", "Invalid username or password.")
        return

    # Students need the admin's permission before they can enter
    if person["role"] != "admin":
        if person["status"] == "pending":
            messagebox.showinfo("Waiting for Approval",
                                "Your account is waiting for admin approval.")
            return
        elif person["status"] == "revoked":
            messagebox.showerror("Access Denied",
                                 "The admin has removed your access.")
            return

    current_user["username"] = person["username"]
    current_user["role"] = person["role"]
    load_materials()
    show_main_screen()


def register_user():
    """Create a new student account with status 'pending'."""
    username = clean_text(reg_username.get())
    password = reg_password.get()
    confirm = reg_confirm.get()

    if username == "" or password == "" or confirm == "":
        messagebox.showwarning("Missing Information", "Please fill all fields.",
                               parent=register_window)
        return
    if " " in username:
        messagebox.showerror("Invalid Username", "Username cannot contain spaces.",
                             parent=register_window)
        return
    if len(password) < 4:
        messagebox.showerror("Weak Password",
                             "Password must have at least 4 characters.",
                             parent=register_window)
        return
    if password != confirm:
        messagebox.showerror("Mismatch", "Passwords do not match.",
                             parent=register_window)
        return

    load_users()
    if find_user(username) is not None:
        messagebox.showerror("Username Taken", "This username already exists.",
                             parent=register_window)
        return

    users.append({"username": username, "password": hash_password(password),
                  "role": "user", "status": "pending"})
    if save_users():
        messagebox.showinfo("Registered",
                            "Account created! Ask the admin to grant you access.",
                            parent=register_window)
        register_window.destroy()


def open_register_window():
    """Small window where a new student creates an account."""
    global register_window, reg_username, reg_password, reg_confirm
    register_window = tk.Toplevel(root)
    register_window.title("Register New Student")
    register_window.geometry("340x260")
    register_window.configure(bg=WHITE)
    register_window.grab_set()                  # block the main window

    font = ("Segoe UI", 10)
    tk.Label(register_window, text="Username:", font=font, bg=WHITE
             ).pack(pady=(18, 2))
    reg_username = tk.Entry(register_window, font=font, width=28)
    reg_username.pack()
    tk.Label(register_window, text="Password:", font=font, bg=WHITE
             ).pack(pady=(10, 2))
    reg_password = tk.Entry(register_window, font=font, width=28, show="*")
    reg_password.pack()
    tk.Label(register_window, text="Confirm Password:", font=font, bg=WHITE
             ).pack(pady=(10, 2))
    reg_confirm = tk.Entry(register_window, font=font, width=28, show="*")
    reg_confirm.pack()
    tk.Button(register_window, text="Register", command=register_user,
              font=("Segoe UI", 10, "bold"), bg=DARK_BLUE, fg=WHITE,
              relief="flat", cursor="hand2", padx=20).pack(pady=18)
    reg_username.focus()


def logout():
    """Forget the current user and go back to the login screen."""
    current_user.clear()
    show_login_screen()


# ----------------------------------------------------------------------
# TABLE DISPLAY HELPER
# ----------------------------------------------------------------------
def show_in_table(record_list):
    """Clear the table and fill it with the given list of records."""
    for row in table.get_children():
        table.delete(row)
    for item in record_list:
        # iid=item["id"] lets us read the exact ID back when a row is clicked
        table.insert("", "end", iid=item["id"],
                     values=(item["id"], item["title"], item["subject"],
                             item["module"], item["type"], item["path"],
                             item["description"]))
    count_label.config(text="Showing " + str(len(record_list)) + " record(s)")


# ----------------------------------------------------------------------
# 10. CLEAR FIELDS (admin form)
# ----------------------------------------------------------------------
def clear_fields():
    """Empty every input box and reset the dropdown."""
    if not is_admin():
        return
    id_entry.delete(0, tk.END)
    title_entry.delete(0, tk.END)
    subject_entry.delete(0, tk.END)
    module_entry.delete(0, tk.END)
    path_entry.delete(0, tk.END)
    description_text.delete("1.0", tk.END)
    type_combo.set(MATERIAL_TYPES[0])
    id_entry.focus()


def browse_file():
    """Open a file dialog so the admin can choose a PDF or PPT file."""
    chosen = filedialog.askopenfilename(
        title="Select a PDF or PowerPoint file",
        filetypes=[("PDF and PowerPoint", "*.pdf *.ppt *.pptx"),
                   ("PDF files", "*.pdf"),
                   ("PowerPoint files", "*.ppt *.pptx")])
    if chosen != "":
        path_entry.delete(0, tk.END)
        path_entry.insert(0, chosen)
        # Suggest the file name as the title if the title is still empty
        if title_entry.get().strip() == "":
            name = os.path.splitext(os.path.basename(chosen))[0]
            title_entry.insert(0, name)


# ----------------------------------------------------------------------
# 6. ADD MATERIAL (ADMIN ONLY) - uploads the file
# ----------------------------------------------------------------------
def add_material():
    """Validate the form, copy the file into 'uploads', save the record."""
    # Access control: only the admin may add materials
    if not is_admin():
        messagebox.showerror("Access Denied", "Only the admin can add materials.")
        return

    material_id = clean_text(id_entry.get())
    title = clean_text(title_entry.get())
    subject = clean_text(subject_entry.get())
    module = clean_text(module_entry.get())
    material_type = type_combo.get()
    source_path = path_entry.get().strip()
    description = clean_text(description_text.get("1.0", tk.END))

    # Required fields must not be empty
    if title == "" or subject == "" or module == "" or source_path == "":
        messagebox.showwarning("Missing Information",
                               "Please fill Title, Subject, Module Number and "
                               "choose a file using Browse.")
        return

    # The chosen file must exist and must be a PDF or PPT
    if not os.path.isfile(source_path):
        messagebox.showerror("File Not Found", "The selected file does not exist.")
        return
    extension = os.path.splitext(source_path)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        messagebox.showerror("Invalid File",
                             "Only PDF, PPT and PPTX files can be uploaded.")
        return

    # Module number must be a positive whole number
    try:
        module_number = int(module)
        if module_number <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Input",
                             "Module Number must be a positive whole number.")
        return

    # Generate an ID if empty, otherwise validate it and check duplicates
    if material_id == "":
        material_id = generate_id()
    elif not is_valid_id(material_id):
        messagebox.showerror("Invalid ID",
                             "ID can contain only letters, digits, - and _")
        return
    elif id_exists(material_id):
        messagebox.showerror("Duplicate ID",
                             "Material ID '" + material_id + "' already exists.")
        return

    # Build the stored file name: ID + original name (spaces become _)
    original_name = clean_text(os.path.basename(source_path)).replace(" ", "_")
    stored_name = material_id + "_" + original_name
    destination = os.path.join(UPLOAD_FOLDER, stored_name)

    # Copy the file into the uploads folder (this is the actual upload)
    try:
        create_upload_folder()
        shutil.copy(source_path, destination)
    except OSError:
        messagebox.showerror("Upload Failed", "Could not copy the file.")
        return

    # Store the material in a dictionary and add it to the list
    new_material = {
        "id": material_id,
        "title": title,
        "subject": subject,
        "module": str(module_number),
        "type": material_type,
        "path": stored_name,
        "description": description,
    }
    materials.append(new_material)

    if append_material_to_file(new_material):
        messagebox.showinfo("Success",
                            "File uploaded and material added with ID: " + material_id)
        clear_fields()
        show_in_table(materials)
    else:
        materials.remove(new_material)          # undo if saving failed
        try:
            os.remove(destination)
        except OSError:
            pass


# ----------------------------------------------------------------------
# 7. VIEW ALL MATERIALS
# ----------------------------------------------------------------------
def view_materials():
    """Reload the file and show every record in the table."""
    if not has_access():
        return
    load_materials()
    search_entry.delete(0, tk.END)
    show_in_table(materials)
    if len(materials) == 0:
        messagebox.showinfo("No Materials", "No study materials available yet.")


# ----------------------------------------------------------------------
# 8. SEARCH MATERIAL
# ----------------------------------------------------------------------
def search_material():
    """Search ID, title, subject, module and type (case-insensitive)."""
    if not has_access():
        return
    keyword = search_entry.get().strip().lower()
    if keyword == "":
        messagebox.showwarning("Empty Search", "Please type a keyword to search.")
        return

    results = []
    for item in materials:
        for field in ["id", "title", "subject", "module", "type"]:
            if keyword in item[field].lower():
                results.append(item)
                break

    show_in_table(results)
    if len(results) == 0:
        messagebox.showinfo("No Match", "No material found for '" + keyword + "'.")


# ----------------------------------------------------------------------
# OPEN A MATERIAL FILE (admin and approved users)
# ----------------------------------------------------------------------
def open_material():
    """Open the selected PDF/PPT using the computer's default program."""
    if not has_access():
        return
    selected = table.selection()
    if len(selected) == 0:
        messagebox.showwarning("No Selection", "Click a row in the table first.")
        return

    item = find_material(selected[0])
    if item is None:
        messagebox.showerror("Not Found", "Record not found.")
        return

    full_path = os.path.join(UPLOAD_FOLDER, item["path"])
    if not os.path.isfile(full_path):
        messagebox.showerror("File Missing",
                             "The file '" + item["path"] + "' is not in the "
                             "uploads folder.")
        return

    try:
        if sys.platform.startswith("win"):
            os.startfile(full_path)                     # Windows
        elif sys.platform == "darwin":
            subprocess.call(["open", full_path])        # Mac
        else:
            subprocess.call(["xdg-open", full_path])    # Linux
    except OSError:
        messagebox.showerror("Open Failed", "Could not open the file.")


# ----------------------------------------------------------------------
# 9. DELETE MATERIAL (ADMIN ONLY)
# ----------------------------------------------------------------------
def on_row_select(event):
    """For the admin: copy the clicked row's ID into the Material ID box."""
    selected = table.selection()
    if len(selected) > 0 and is_admin():
        id_entry.delete(0, tk.END)
        id_entry.insert(0, selected[0])


def delete_material():
    """Delete a material (record and uploaded file) using its ID."""
    if not is_admin():
        messagebox.showerror("Access Denied", "Only the admin can delete materials.")
        return

    material_id = id_entry.get().strip()
    if material_id == "":
        messagebox.showwarning("No ID",
                               "Enter a Material ID or click a row to delete.")
        return

    found = find_material(material_id)
    if found is None:
        messagebox.showerror("Not Found",
                             "No material with ID '" + material_id + "'.")
        return

    answer = messagebox.askyesno("Confirm Delete",
                                 "Delete '" + found["title"] + "' (" +
                                 found["id"] + ") and its file?")
    if answer:
        materials.remove(found)
        if save_materials():
            # Also remove the uploaded file from the uploads folder
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, found["path"]))
            except OSError:
                pass                    # file was already missing - ignore
            messagebox.showinfo("Deleted", "Material deleted successfully.")
            clear_fields()
            show_in_table(materials)


# ----------------------------------------------------------------------
# MANAGE USERS (ADMIN ONLY) - grant / revoke access
# ----------------------------------------------------------------------
def refresh_user_table():
    """Reload users.txt and show every student in the manager window."""
    load_users()
    for row in user_table.get_children():
        user_table.delete(row)
    for person in users:
        if person["role"] != "admin":
            user_table.insert("", "end", iid=person["username"],
                              values=(person["username"], person["status"]))


def set_user_status(new_status):
    """Change the selected student's status (approved / revoked)."""
    selected = user_table.selection()
    if len(selected) == 0:
        messagebox.showwarning("No Selection", "Click a student first.",
                               parent=manager_window)
        return
    person = find_user(selected[0])
    if person is not None:
        person["status"] = new_status
        save_users()
        refresh_user_table()


def delete_user():
    """Remove the selected student's account."""
    selected = user_table.selection()
    if len(selected) == 0:
        messagebox.showwarning("No Selection", "Click a student first.",
                               parent=manager_window)
        return
    person = find_user(selected[0])
    if person is not None:
        if messagebox.askyesno("Confirm", "Delete user '" + person["username"] + "'?",
                               parent=manager_window):
            users.remove(person)
            save_users()
            refresh_user_table()


def open_user_manager():
    """Window where the admin approves or blocks students."""
    global manager_window, user_table
    if not is_admin():
        messagebox.showerror("Access Denied", "Only the admin can manage users.")
        return

    manager_window = tk.Toplevel(root)
    manager_window.title("Manage Users - Grant Access")
    manager_window.geometry("520x440")
    manager_window.configure(bg=LIGHT_GREY)
    manager_window.grab_set()

    tk.Label(manager_window, text="Student Accounts", font=("Segoe UI", 14, "bold"),
             bg=LIGHT_GREY, fg=DARK_BLUE).pack(pady=(12, 2))
    tk.Label(manager_window,
             text="pending = waiting, approved = can view, revoked = blocked",
             font=("Segoe UI", 9), bg=LIGHT_GREY).pack()

    user_table = ttk.Treeview(manager_window, columns=("Username", "Status"),
                              show="headings", height=11)
    user_table.heading("Username", text="Username")
    user_table.heading("Status", text="Status")
    user_table.column("Username", width=250)
    user_table.column("Status", width=150)
    user_table.pack(padx=15, pady=10, fill="both", expand=True)

    buttons = tk.Frame(manager_window, bg=LIGHT_GREY)
    buttons.pack(pady=(0, 12))
    tk.Button(buttons, text="Grant Access", bg=GREEN, fg=WHITE, relief="flat",
              font=("Segoe UI", 10, "bold"), padx=10, cursor="hand2",
              command=lambda: set_user_status("approved")).pack(side="left", padx=5)
    tk.Button(buttons, text="Revoke Access", bg="#C77700", fg=WHITE, relief="flat",
              font=("Segoe UI", 10, "bold"), padx=10, cursor="hand2",
              command=lambda: set_user_status("revoked")).pack(side="left", padx=5)
    tk.Button(buttons, text="Delete User", bg=RED, fg=WHITE, relief="flat",
              font=("Segoe UI", 10, "bold"), padx=10, cursor="hand2",
              command=delete_user).pack(side="left", padx=5)

    refresh_user_table()


# ----------------------------------------------------------------------
# 11. EXIT APPLICATION
# ----------------------------------------------------------------------
def exit_application():
    """Ask for confirmation, then close the window."""
    if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
        root.destroy()


# ----------------------------------------------------------------------
# GUI: HEADER (always visible) AND THE AREA BELOW IT
# ----------------------------------------------------------------------
root.configure(bg=LIGHT_GREY)

header = tk.Frame(root, bg=DARK_BLUE)
header.pack(fill="x")
tk.Label(header, text="Student Study Material Management System",
         font=("Segoe UI", 20, "bold"), bg=DARK_BLUE, fg=WHITE
         ).pack(pady=(12, 0))
tk.Label(header, text="Organize your study resources in one place.",
         font=("Segoe UI", 11), bg=DARK_BLUE, fg="#C9D6E8"
         ).pack(pady=(0, 12))

# 'screen' holds either the login page or the main dashboard
screen = tk.Frame(root, bg=LIGHT_GREY)
screen.pack(fill="both", expand=True)

# Table look
style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                background=DARK_BLUE, foreground=WHITE)
style.configure("Treeview", rowheight=24, font=("Segoe UI", 10))


# ----------------------------------------------------------------------
# GUI: LOGIN SCREEN
# ----------------------------------------------------------------------
def show_login_screen():
    """Build the login page."""
    global username_entry, password_entry
    clear_screen()

    card = tk.Frame(screen, bg=WHITE, padx=45, pady=30,
                    highlightbackground=DARK_BLUE, highlightthickness=2)
    card.place(relx=0.5, rely=0.42, anchor="center")

    font = ("Segoe UI", 11)
    tk.Label(card, text="Login", font=("Segoe UI", 18, "bold"),
             bg=WHITE, fg=DARK_BLUE).pack(pady=(0, 15))
    tk.Label(card, text="Username", font=font, bg=WHITE).pack(anchor="w")
    username_entry = tk.Entry(card, font=font, width=28)
    username_entry.pack(pady=(2, 10))
    tk.Label(card, text="Password", font=font, bg=WHITE).pack(anchor="w")
    password_entry = tk.Entry(card, font=font, width=28, show="*")
    password_entry.pack(pady=(2, 15))

    tk.Button(card, text="Login", command=login, font=("Segoe UI", 11, "bold"),
              bg=DARK_BLUE, fg=WHITE, relief="flat", cursor="hand2", width=24
              ).pack(pady=3)
    tk.Button(card, text="New Student? Register", command=open_register_window,
              font=("Segoe UI", 10), bg=MID_BLUE, fg=WHITE, relief="flat",
              cursor="hand2", width=24).pack(pady=3)
    tk.Button(card, text="Exit", command=exit_application,
              font=("Segoe UI", 10), bg="#555555", fg=WHITE, relief="flat",
              cursor="hand2", width=24).pack(pady=3)

    password_entry.bind("<Return>", lambda event: login())   # Enter key logs in
    username_entry.focus()


# ----------------------------------------------------------------------
# GUI: MAIN DASHBOARD (different for admin and user)
# ----------------------------------------------------------------------
def make_nav_button(parent, text, command, colour=DARK_BLUE):
    """Create one sidebar button."""
    tk.Button(parent, text=text, command=command,
              font=("Segoe UI", 11, "bold"), bg=colour, fg=WHITE,
              activebackground=WHITE, activeforeground=DARK_BLUE,
              relief="flat", cursor="hand2", pady=7
              ).pack(fill="x", padx=15, pady=5)


def show_main_screen():
    """Build the dashboard. The admin sees extra buttons and the input form."""
    global table, count_label, search_entry
    global id_entry, title_entry, subject_entry, module_entry
    global type_combo, path_entry, description_text
    clear_screen()

    body = tk.Frame(screen, bg=LIGHT_GREY)
    body.pack(fill="both", expand=True)

    # ---- Sidebar ----
    sidebar = tk.Frame(body, bg=MID_BLUE, width=215)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    if is_admin():
        role_text = "Admin"
    else:
        role_text = "Student"
    tk.Label(sidebar, text="Logged in as:", font=("Segoe UI", 9),
             bg=MID_BLUE, fg="#C9D6E8").pack(pady=(14, 0))
    tk.Label(sidebar, text=current_user["username"] + " (" + role_text + ")",
             font=("Segoe UI", 11, "bold"), bg=MID_BLUE, fg=WHITE).pack(pady=(0, 8))

    if is_admin():
        make_nav_button(sidebar, "Add Study Material", add_material)
    make_nav_button(sidebar, "View All Materials", view_materials)
    make_nav_button(sidebar, "Search Material", search_material)
    make_nav_button(sidebar, "Open Selected File", open_material, GREEN)
    if is_admin():
        make_nav_button(sidebar, "Delete Material", delete_material, RED)
        make_nav_button(sidebar, "Manage Users", open_user_manager, "#7B4FA0")
        make_nav_button(sidebar, "Clear Fields", clear_fields)
    make_nav_button(sidebar, "Logout", logout, "#C77700")
    make_nav_button(sidebar, "Exit Application", exit_application, "#555555")

    # ---- Content area ----
    content = tk.Frame(body, bg=LIGHT_GREY)
    content.pack(side="left", fill="both", expand=True, padx=15, pady=10)

    font = ("Segoe UI", 10)

    # ---- Input form (ADMIN ONLY) ----
    if is_admin():
        form = tk.LabelFrame(content, text=" Upload Study Material (Admin) ",
                             font=("Segoe UI", 11, "bold"), bg=WHITE, fg=DARK_BLUE,
                             padx=10, pady=8)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        def make_label(text, row, column):
            tk.Label(form, text=text, font=font, bg=WHITE, anchor="w"
                     ).grid(row=row, column=column, sticky="w", padx=5, pady=5)

        make_label("Material ID:", 0, 0)
        id_entry = tk.Entry(form, font=font)
        id_entry.grid(row=0, column=1, sticky="ew", padx=5)

        make_label("Material Title:", 0, 2)
        title_entry = tk.Entry(form, font=font)
        title_entry.grid(row=0, column=3, sticky="ew", padx=5)

        make_label("Subject Name:", 1, 0)
        subject_entry = tk.Entry(form, font=font)
        subject_entry.grid(row=1, column=1, sticky="ew", padx=5)

        make_label("Module Number:", 1, 2)
        module_entry = tk.Entry(form, font=font)
        module_entry.grid(row=1, column=3, sticky="ew", padx=5)

        make_label("Material Type:", 2, 0)
        type_combo = ttk.Combobox(form, values=MATERIAL_TYPES, state="readonly",
                                  font=font)
        type_combo.grid(row=2, column=1, sticky="ew", padx=5)
        type_combo.set(MATERIAL_TYPES[0])

        make_label("PDF / PPT File:", 2, 2)
        file_row = tk.Frame(form, bg=WHITE)
        file_row.grid(row=2, column=3, sticky="ew", padx=5)
        path_entry = tk.Entry(file_row, font=font)
        path_entry.pack(side="left", fill="x", expand=True)
        tk.Button(file_row, text="Browse...", command=browse_file, font=font,
                  bg=MID_BLUE, fg=WHITE, relief="flat", cursor="hand2"
                  ).pack(side="left", padx=(5, 0))

        make_label("Description:", 3, 0)
        description_text = tk.Text(form, height=3, font=font)
        description_text.grid(row=3, column=1, columnspan=3, sticky="ew",
                              padx=5, pady=5)
    else:
        tk.Label(content, text="You have view-only access. Select a material "
                 "and click 'Open Selected File'.", font=("Segoe UI", 10, "italic"),
                 bg=LIGHT_GREY, fg=DARK_BLUE).pack(anchor="w", pady=(0, 4))

    # ---- Search bar ----
    search_frame = tk.LabelFrame(content, text=" Search ",
                                 font=("Segoe UI", 11, "bold"), bg=WHITE,
                                 fg=DARK_BLUE, padx=10, pady=8)
    search_frame.pack(fill="x", pady=8)
    search_frame.columnconfigure(1, weight=1)

    tk.Label(search_frame, text="Keyword (ID, title, subject, module, type):",
             font=font, bg=WHITE).grid(row=0, column=0, padx=5)
    search_entry = tk.Entry(search_frame, font=font)
    search_entry.grid(row=0, column=1, sticky="ew", padx=5)
    tk.Button(search_frame, text="Search", command=search_material,
              font=("Segoe UI", 10, "bold"), bg=DARK_BLUE, fg=WHITE,
              relief="flat", cursor="hand2", padx=15).grid(row=0, column=2, padx=5)

    # ---- Table ----
    table_frame = tk.Frame(content, bg=LIGHT_GREY)
    table_frame.pack(fill="both", expand=True)

    columns = ("ID", "Title", "Subject", "Module", "Type", "File", "Description")
    table = ttk.Treeview(table_frame, columns=columns, show="headings")
    widths = [70, 170, 120, 65, 110, 170, 200]
    for i in range(len(columns)):
        table.heading(columns[i], text=columns[i])
        table.column(columns[i], width=widths[i], anchor="w")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)
    table.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    table.bind("<<TreeviewSelect>>", on_row_select)
    table.bind("<Double-1>", lambda event: open_material())  # double-click opens

    count_label = tk.Label(content, text="", font=("Segoe UI", 9),
                           bg=LIGHT_GREY, fg=DARK_BLUE, anchor="w")
    count_label.pack(fill="x", pady=(4, 0))

    show_in_table(materials)


# ----------------------------------------------------------------------
# 12. START THE APPLICATION
# ----------------------------------------------------------------------
root.protocol("WM_DELETE_WINDOW", exit_application)
create_upload_folder()
load_users()                # creates users.txt with the admin on first run
show_login_screen()
root.mainloop()
