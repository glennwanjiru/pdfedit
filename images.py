import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkthemes import ThemedTk
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from PIL import Image
import tempfile
import os
import threading

def create_combined_page(pdf_path, page_numbers, separate_with_line, dpi, maintain_aspect_ratio):
    packet = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    can = canvas.Canvas(packet.name, pagesize=landscape(A4))
    page_width, page_height = landscape(A4)

    images = convert_from_path(pdf_path, dpi=dpi, first_page=min(page_numbers)+1, last_page=max(page_numbers)+1)
    for index, img in enumerate(images):
        x_offset = (page_width / len(page_numbers)) * index
        add_image_to_canvas(img, x_offset, page_width / len(page_numbers), page_height, can, maintain_aspect_ratio)

    if separate_with_line and len(page_numbers) > 1:
        line_x = page_width / len(page_numbers)
        can.setStrokeColor("black")
        can.setLineWidth(1)
        for i in range(1, len(page_numbers)):
            can.line(line_x * i, 0, line_x * i, page_height)

    can.save()
    return packet.name

def add_image_to_canvas(img, x_offset, width, height, can, maintain_aspect_ratio):
    original_width, original_height = img.size
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

    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        img_resized = img.resize((int(scaled_width), int(scaled_height)), Image.LANCZOS)
        img_resized.save(tmp_file, format='PNG')
        tmp_file_path = tmp_file.name

    can.drawImage(tmp_file_path, x_offset + (width - scaled_width) / 2, 0, width=scaled_width, height=scaled_height)
    os.remove(tmp_file_path)

def reformat_pdf(input_pdf, output_pdf, num_pages, separate_with_line, dpi, maintain_aspect_ratio, progress, status_label):
    try:
        from PyPDF2 import PdfReader, PdfWriter
        pdf_reader = PdfReader(input_pdf)
        pdf_writer = PdfWriter()
        num_total_pages = len(pdf_reader.pages)
        num_combined_pages = 0

        for i in range(0, num_total_pages, num_pages):
            page_numbers = range(i, min(i + num_pages, num_total_pages))
            combined_page_path = create_combined_page(input_pdf, page_numbers, separate_with_line, dpi, maintain_aspect_ratio)
            combined_pdf = PdfReader(combined_page_path)
            pdf_writer.add_page(combined_pdf.pages[0])
            num_combined_pages += 1
            progress.set((i + num_pages) / num_total_pages * 100)
            os.remove(combined_page_path)

        with open(output_pdf, "wb") as out_f:
            pdf_writer.write(out_f)

        status_label.config(text="PDF reformatted successfully!", foreground="green")
    except Exception as e:
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
    num_pages = int(num_pages_var.get())
    separate_with_line = separate_var.get()
    dpi = int(dpi_var.get())
    maintain_aspect_ratio = aspect_ratio_var.get()
    if not input_pdf or not output_pdf:
        messagebox.showerror("Error", "Please select both input and output PDF files.")
        return
    progress.set(0)
    status_label.config(text="")
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
app = ThemedTk(theme="breeze")  # You can choose any theme from ttkthemes
app.title("PDF Reformatter")

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

tk.Label(app, text="Pages to combine:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
tk.Entry(app, textvariable=num_pages_var, width=5).grid(row=2, column=1, padx=10, pady=10, sticky="w")

tk.Label(app, text="Output Quality (DPI):").grid(row=3, column=0, padx=10, pady=10, sticky="e")
dpi_dropdown = ttk.Combobox(app, textvariable=dpi_var, values=["72", "150", "300", "600", "1200", "2500"])
dpi_dropdown.grid(row=3, column=1, padx=10, pady=10, sticky="w")
dpi_dropdown.set("150")

tk.Checkbutton(app, text="Separate pages with a line", variable=separate_var).grid(row=4, column=1, padx=10, pady=10, sticky="w")

tk.Checkbutton(app, text="Maintain aspect ratio", variable=aspect_ratio_var).grid(row=5, column=1, padx=10, pady=10, sticky="w")

tk.Button(app, text="Reformat PDF", command=process_pdf).grid(row=6, column=1, pady=20, sticky="e")
tk.Button(app, text="Clear", command=clear_form).grid(row=6, column=2, pady=20, sticky="w")

progress_bar = ttk.Progressbar(app, orient="horizontal", length=400, mode="determinate", variable=progress)
progress_bar.grid(row=7, column=0, columnspan=3, padx=10, pady=10)

status_label = tk.Label(app, text="")
status_label.grid(row=8, column=0, columnspan=3, padx=10, pady=10)

app.mainloop()
