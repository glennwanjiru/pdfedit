import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkthemes import ThemedTk
from PyPDF2 import PdfWriter
import pdfplumber
import fitz  # PyMuPDF
import io
import tempfile
import os
import threading
import logging
import tkinter.font as tkfont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from PIL import Image  # Ensure you import PIL for image handling

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_tooltip(widget, text):
    def enter(event):
        x = y = 0
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tip, text=text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
    
    def leave(event):
        widget.unbind('<Enter>', widget.tooltip_id)
        widget.unbind('<Leave>', widget.tooltip_leave_id)
        if widget.tooltip:
            widget.tooltip.destroy()
        widget.tooltip = None
    
    widget.tooltip = None
    widget.tooltip_id = widget.bind('<Enter>', enter)
    widget.tooltip_leave_id = widget.bind('<Leave>', leave)

def create_combined_page(pdf_reader, page_numbers, separate_with_line, dpi, maintain_aspect_ratio):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=landscape(A4))
    page_width, page_height = landscape(A4)
    
    for index, page_num in enumerate(page_numbers):
        if page_num < len(pdf_reader.pages):
            x_offset = (page_width / len(page_numbers)) * index
            add_page_to_canvas(pdf_reader, page_num, x_offset, page_width / len(page_numbers), page_height, can, dpi, maintain_aspect_ratio)
    
    if separate_with_line and len(page_numbers) > 1:
        line_x = page_width / len(page_numbers)
        can.setStrokeColor("black")
        can.setLineWidth(1)
        for i in range(1, len(page_numbers)):
            can.line(line_x * i, 0, line_x * i, page_height)
    
    can.save()
    packet.seek(0)
    new_pdf = fitz.open(stream=packet.read(), filetype="pdf")
    return new_pdf[0]

def add_page_to_canvas(pdf_reader, page_num, x_offset, width, height, can, dpi, maintain_aspect_ratio):
    page = pdf_reader.pages[page_num]
    text = extract_text_from_page(page)
    
    pdf_writer = PdfWriter()
    pdf_writer.add_page(page)
    temp_pdf = io.BytesIO()
    pdf_writer.write(temp_pdf)
    temp_pdf.seek(0)
    
    doc = fitz.open(stream=temp_pdf, filetype="pdf")
    page = doc[0]
    
    original_width, original_height = page.rect.width, page.rect.height
    aspect_ratio = original_width / original_height
    
    if maintain_aspect_ratio:
        scaled_height = height
        scaled_width = height * aspect_ratio
        
        if scaled_width > width:
            scaled_width = width
            scaled_height = width / aspect_ratio
    else:
        scaled_width = width
        scaled_height = height
    
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img_resized = img.resize((int(scaled_width), int(scaled_height)), Image.LANCZOS)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        img_resized.save(tmp_file, format='PNG', dpi=(dpi, dpi))
        tmp_file_path = tmp_file.name
    
    can.drawImage(tmp_file_path, x_offset + (width - scaled_width) / 2, 0, width=scaled_width, height=scaled_height)
    os.remove(tmp_file_path)
    
    can.drawString(x_offset + 10, height - 20, text)

def extract_text_from_page(page):
    with io.BytesIO(page.get_contents()) as temp_pdf:
        with pdfplumber.open(temp_pdf) as pdf:
            return pdf.pages[0].extract_text() or ""

def reformat_pdf(input_pdf, output_pdf, num_pages, separate_with_line, dpi, maintain_aspect_ratio, progress, status_label):
    try:
        pdf_reader = fitz.open(input_pdf)
        pdf_writer = PdfWriter()
        num_total_pages = len(pdf_reader)
        num_combined_pages = 0

        for i in range(0, num_total_pages, num_pages):
            page_numbers = list(range(i, min(i + num_pages, num_total_pages)))
            combined_page = create_combined_page(pdf_reader, page_numbers, separate_with_line, dpi, maintain_aspect_ratio)
            pdf_writer.add_page(combined_page)
            num_combined_pages += 1
            progress.set((i + num_pages) / num_total_pages * 100)

        with open(output_pdf, "wb") as out_f:
            pdf_writer.write(out_f)
        
        logging.info(f"PDF reformatted successfully. Output: {output_pdf}")
        status_label.config(text="PDF reformatted successfully!", foreground="green")
    except Exception as e:
        logging.error(f"Error reformatting PDF: {str(e)}")
        status_label.config(text=f"Error: {str(e)}", foreground="red")

def select_input_pdf():
    input_pdf = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if input_pdf:
        input_path.set(input_pdf)

def select_output_pdf():
    output_pdf = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if output_pdf:
        output_path.set(output_pdf)

def process_pdf():
    input_pdf = input_path.get()
    output_pdf = output_path.get()
    
    if not input_pdf or not output_pdf:
        messagebox.showerror("Error", "Please select both input and output PDF files.")
        return
    
    try:
        num_pages = int(num_pages_var.get())
        if num_pages <= 0:
            raise ValueError("Number of pages must be positive")
    except ValueError:
        messagebox.showerror("Error", "Invalid number of pages. Please enter a positive integer.")
        return
    
    try:
        dpi = int(dpi_var.get())
        if dpi <= 0:
            raise ValueError("DPI must be positive")
    except ValueError:
        messagebox.showerror("Error", "Invalid DPI value. Please enter a positive integer.")
        return
    
    separate_with_line = separate_var.get()
    maintain_aspect_ratio = aspect_ratio_var.get()
    
    progress.set(0)
    status_label.config(text="Processing...")
    threading.Thread(target=reformat_pdf, args=(input_pdf, output_pdf, num_pages, separate_with_line, dpi, maintain_aspect_ratio, progress, status_label)).start()

def clear_form():
    input_path.set("")
    output_path.set("")
    num_pages_var.set("2")
    separate_var.set(False)
    dpi_var.set("150")
    aspect_ratio_var.set(True)
    progress.set(0)
    status_label.config(text="")

# Create themed Tk window
app = ThemedTk(theme="breeze")
app.title("PDF Reformatter")
app.geometry("600x500")

# Use a more readable font
default_font = tkfont.nametofont("TkDefaultFont")
default_font.configure(size=10)
app.option_add("*Font", default_font)

input_path = tk.StringVar()
output_path = tk.StringVar()
num_pages_var = tk.StringVar(value="2")
separate_var = tk.BooleanVar(value=False)
dpi_var = tk.StringVar(value="150")
aspect_ratio_var = tk.BooleanVar(value=True)
progress = tk.DoubleVar()

# Layout and Widgets
tk.Label(app, text="Input PDF:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=input_path, width=50).grid(row=0, column=1, padx=10, pady=10)
tk.Button(app, text="Browse...", command=select_input_pdf).grid(row=0, column=2, padx=10, pady=10)

tk.Label(app, text="Output PDF:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=output_path, width=50).grid(row=1, column=1, padx=10, pady=10)
tk.Button(app, text="Browse...", command=select_output_pdf).grid(row=1, column=2, padx=10, pady=10)

tk.Label(app, text="Number of pages per file:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=num_pages_var, width=5).grid(row=2, column=1, padx=10, pady=10, sticky="w")

tk.Label(app, text="DPI:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=dpi_var, width=5).grid(row=3, column=1, padx=10, pady=10, sticky="w")

tk.Checkbutton(app, text="Separate pages with lines", variable=separate_var).grid(row=4, column=1, padx=10, pady=10, sticky="w")
tk.Checkbutton(app, text="Maintain aspect ratio", variable=aspect_ratio_var).grid(row=5, column=1, padx=10, pady=10, sticky="w")

tk.Button(app, text="Reformat PDF", command=process_pdf).grid(row=6, column=1, padx=10, pady=10)
tk.Button(app, text="Clear", command=clear_form).grid(row=6, column=2, padx=10, pady=10)

progress_bar = ttk.Progressbar(app, variable=progress, maximum=100)
progress_bar.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

status_label = tk.Label(app, text="", font=("Helvetica", 10, "italic"))
status_label.grid(row=8, column=0, columnspan=3, padx=10, pady=10)

app.mainloop()
