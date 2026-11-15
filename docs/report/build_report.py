#!/usr/bin/env python3
"""Build the eight-page technical report from its Markdown source.

Usage: python docs/report/build_report.py [--output path.pdf]
Dependencies: reportlab, pypdf, Pillow.
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Flowable, Preformatted,
)
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('TECHNICAL_REPORT.md')
PAGE_W, PAGE_H = 612, 792
MARGIN = 48
WIDTH = PAGE_W - MARGIN * 2
INK = colors.HexColor('#17211e')
MUTED = colors.HexColor('#52605b')
ACCENT = colors.HexColor('#a7c63d')
PALE = colors.HexColor('#eef3e6')
LINE = colors.HexColor('#d8dfd9')

styles = {
    'title': ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=25,
                            leading=28, textColor=INK, spaceAfter=15),
    'sub': ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=12,
                          leading=15, textColor=INK, spaceBefore=10, spaceAfter=6),
    'body': ParagraphStyle('Body', fontName='Helvetica', fontSize=9.5,
                           leading=13.3, textColor=INK, spaceAfter=8,
                           splitLongWords=True, allowWidows=0, allowOrphans=0),
    'cell': ParagraphStyle('Cell', fontName='Helvetica', fontSize=8.6,
                           leading=11.4, textColor=INK),
    'headcell': ParagraphStyle('HeadCell', fontName='Helvetica-Bold', fontSize=8.6,
                               leading=11.4, textColor=INK),
    'caption': ParagraphStyle('Caption', fontName='Helvetica', fontSize=8,
                              leading=10.5, textColor=MUTED, spaceAfter=9),
    'reference': ParagraphStyle('Reference', fontName='Helvetica', fontSize=9,
                                leading=12, textColor=INK, spaceAfter=6,
                                splitLongWords=True, allowWidows=0, allowOrphans=0),
    'code': ParagraphStyle('Code', fontName='Courier', fontSize=7.7,
                           leading=10.5, textColor=INK, backColor=PALE,
                           borderPadding=8, spaceAfter=10),
}


def p(text, style='body'):
    safe = escape(text)
    # URL hyperlinks keep the printed URL and permit breaks at punctuation.
    safe = re.sub(r'(https?://[^\s]+)',
                  lambda m: '<link href="' + m.group(1).rstrip('.,;') + '">' + m.group(1) + '</link>', safe)
    return Paragraph(safe, styles[style])


class Diagram(Flowable):
    def __init__(self, kind):
        Flowable.__init__(self)
        self.kind = kind
        self.width = WIDTH
        self.height = {'pipeline': 88, 'validation': 104, 'barnard': 190}[kind]

    def draw(self):
        c = self.canv
        if self.kind == 'pipeline':
            labels = [('IRSA FITS', 'Original bytes'), ('Processor', 'Sky grid + metadata'),
                      ('Comparison', 'Checks beside images'), ('Evidence card', 'Notes + sources')]
            w, gap = 120, 12
            for i, (a, b) in enumerate(labels):
                x = i * (w + gap)
                c.setFillColor(PALE); c.roundRect(x, 25, w, 47, 5, fill=1, stroke=0)
                c.setFillColor(INK); c.setFont('Helvetica-Bold', 10); c.drawString(x + 10, 54, a)
                c.setFillColor(MUTED); c.setFont('Helvetica', 7.5); c.drawString(x + 10, 37, b)
                if i < 3:
                    c.setStrokeColor(MUTED); c.line(x + w + 2, 48, x + w + 10, 48)
                    c.line(x + w + 7, 51, x + w + 10, 48); c.line(x + w + 7, 45, x + w + 10, 48)
            c.setFont('Helvetica', 7.8); c.setFillColor(MUTED)
            c.drawString(0, 10, 'Figure 1. Data and reasoning remain linked throughout the workflow. Schematic, not a benchmark.')
        elif self.kind == 'validation':
            c.setFont('Helvetica-Bold', 10); c.setFillColor(INK)
            c.drawString(0, 88, '183 unique cutouts: independent field-star verdict')
            pass_w = WIDTH * 128 / 183
            c.setFillColor(ACCENT); c.rect(0, 43, pass_w, 29, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#dce3dc')); c.rect(pass_w, 43, WIDTH-pass_w, 29, fill=1, stroke=0)
            c.setFillColor(INK); c.setFont('Helvetica-Bold', 10)
            c.drawString(10, 53, '128 PASS'); c.drawString(pass_w + 10, 53, '55 UNKNOWN')
            c.setFont('Helvetica', 8); c.drawString(0, 26, '0 FAIL in this retained set. UNKNOWN is not a pass.')
            c.setFillColor(MUTED); c.drawString(0, 10, 'Figure 3. Counts from the retained registration audit; no population reliability estimate.')
        else:
            folder = ROOT/'backend/content/presets/barnards_star/case-moving_neighbor'
            paths = [folder/'2025W35_1A_0008_1_D3.png', folder/'2026W34_1A_0431_1_D3.png']
            labels = ['A | 25 Aug 2025 | 2.0062 micrometers', 'C | 19 Aug 2026 | 2.0284 micrometers']
            for i, path in enumerate(paths):
                x = 37 + i * 253
                c.setFillColor(colors.black); c.rect(x, 25, 160, 160, fill=1, stroke=0)
                c.drawImage(ImageReader(str(path)), x, 25, 160, 160, mask='auto')
                c.setFillColor(MUTED); c.setFont('Helvetica', 7.5); c.drawString(i * 253, 12, labels[i])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(ACCENT); canvas.rect(MARGIN, PAGE_H-35, 28, 3, fill=1, stroke=0)
    canvas.setFillColor(MUTED); canvas.setFont('Helvetica', 8)
    canvas.drawString(MARGIN+37, PAGE_H-35, 'PERIGEE / TECHNICAL REPORT')
    canvas.drawRightString(PAGE_W-MARGIN, PAGE_H-35, '15 NOVEMBER 2026')
    canvas.setStrokeColor(LINE); canvas.line(MARGIN, 35, PAGE_W-MARGIN, 35)
    canvas.setFont('Helvetica', 7.5); canvas.drawString(MARGIN, 22, 'NASA Space Apps 2026 | Supporting documentation')
    canvas.drawRightString(PAGE_W-MARGIN, 22, f'{doc.page} / 8')
    canvas.restoreState()


def parse_page(text, reference=False):
    out=[]; lines=text.strip().splitlines(); i=0
    while i < len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        if line.startswith('```'):
            code=[]; i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i+=1
            out.append(Preformatted('\n'.join(code), styles['code'])); i+=1; continue
        if line.startswith('<!-- figure:'):
            kind=line.split(':',1)[1].split('-->')[0].strip()
            out.append(Diagram(kind))
            if kind=='barnard':
                out.append(p('Figure 2. Original processed SPHEREx case PNGs, full field, unchanged. North is up; east is left. Shared display limits. NASA/IPAC IRSA. The saturated core prevents precision astrometry.', 'caption'))
            i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',x) for x in cells): rows.append(cells)
                i+=1
            n=len(rows[0]); widths=([WIDTH*.34,WIDTH*.66] if n==2 else [WIDTH*.20,WIDTH*.41,WIDTH*.39])
            table=Table([[p(cell,'headcell' if ri==0 else 'cell') for cell in row] for ri,row in enumerate(rows)], colWidths=widths, hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE), ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
                ('LINEBELOW',(0,0),(-1,-1),.4,LINE)]))
            out.extend([table,Spacer(1,10)]);continue
        if line.startswith('# '):out.append(p(line[2:],'title'));i+=1;continue
        if line.startswith('## '):out.append(p(line[3:],'sub'));i+=1;continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','<!--')):
            paragraph.append(lines[i].strip());i+=1
        out.append(p(' '.join(paragraph), 'reference' if reference else 'body'))
    return out


def build(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    sections=SOURCE.read_text().split('---PAGE---')
    if len(sections)!=8:raise ValueError(f'Expected eight source sections, got {len(sections)}')
    doc=BaseDocTemplate(str(output),pagesize=(PAGE_W,PAGE_H),leftMargin=MARGIN,rightMargin=MARGIN,
        topMargin=57,bottomMargin=48,title='Perigee: Guided investigation of SPHEREx images',author='Team Perigee',
        subject='Methods, validation and limitations of the NASA Space Apps 2026 prototype')
    frame=Frame(MARGIN,48,WIDTH,PAGE_H-105,leftPadding=0,bottomPadding=0,rightPadding=0,topPadding=0)
    doc.addPageTemplates(PageTemplate(id='report',frames=[frame],onPage=footer))
    story=[]
    for i,section in enumerate(sections):
        if i:story.append(PageBreak())
        story.extend(parse_page(section, reference=i==7))
    doc.build(story)
    reader=PdfReader(str(output))
    if len(reader.pages)!=8:raise RuntimeError(f'Layout overflow: expected8 pages, got {len(reader.pages)}')
    print(f'Built {output} ({len(reader.pages)} pages)')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'frontend/public/demo/perigee-technical-report.pdf')
    build(parser.parse_args().output.resolve())
