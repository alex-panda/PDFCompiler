from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()
#pdf.add_font('CMUSerif-UprightItalic', fname=os.path.abspath('./src/Fonts/Computer Modern/cmunui.ttf'), uni=True)
#pdf.set_font('CMUSerif-UprightItalic', size=16)
pdf.add_font('BerlinSansFB-Bold', fname='C:\\Windows\\Fonts\\VINERITC.TTF', uni=True)
pdf.set_font('BerlinSansFB-Bold')
pdf.cell(40, 10, "Hello World! (It's a great day today!)")
pdf.output("test.pdf")
