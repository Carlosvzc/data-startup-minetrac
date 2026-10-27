from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,Image
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT,TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import html,re,shutil
from pdf_portada import portada
import matplotlib
R=Path(__file__).resolve().parents[1]
def buscar_fuente(candidatas):
 for c in candidatas:
  if Path(c).exists():return c
 raise SystemExit('No encontramos Arial ni una fuente equivalente: '+', '.join(candidatas))
# Arial en Windows; en Linux usamos Liberation Sans, que tiene las mismas medidas que Arial.
for n,rutas in [('A',['C:/Windows/Fonts/arial.ttf','/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']),('AB',['C:/Windows/Fonts/arialbd.ttf','/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'])]:
 pdfmetrics.registerFont(TTFont(n,buscar_fuente(rutas)))
pdfmetrics.registerFontFamily('A',normal='A',bold='AB',italic='A',boldItalic='AB')
st=getSampleStyleSheet()
st.add(ParagraphStyle(name='BodyM',fontName='A',alignment=TA_JUSTIFY,fontSize=9.5,leading=14,spaceAfter=8,textColor=colors.HexColor('#000000')))
st.add(ParagraphStyle(name='BodyL',parent=st['BodyM'],alignment=TA_LEFT))
st.add(ParagraphStyle(name='SmallM',parent=st['BodyM'],alignment=TA_LEFT,fontSize=8,leading=11,spaceAfter=3))
for lev,size in [(1,24),(2,14),(3,11)]:
 st.add(ParagraphStyle(name='H'+str(lev)+'M',fontName='AB',fontSize=size,leading=size*1.3,spaceBefore=14,spaceAfter=9,textColor=colors.HexColor('#000000'),keepWithNext=True))
def inline(t):
 t=html.escape(t.strip())
 t=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',t)
 t=re.sub(r'`(.*?)`',r'\1',t)
 t=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#000000">\1</link>',t)
 return t
def foot(c,d):
 c.setStrokeColor(colors.HexColor('#000000'));c.line(44,40,551,40)
 c.setFont('A',8);c.setFillColor(colors.HexColor('#000000'))
 c.drawString(44,27,'MineTrac · E0')
 c.drawRightString(551,27,str(d.page))
lines=(R/'docs/E0-propuesta.md').read_text(encoding='utf-8-sig').splitlines()
story=portada('E0','A','AB');i=0
while i<len(lines):
 t=lines[i].strip()
 if not t or t=='---':i+=1;continue
 if t.startswith('|'):
  rows=[]
  while i<len(lines) and lines[i].strip().startswith('|'):
   cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
   if not all(re.fullmatch(r'[:\- ]+',c or '-') for c in cells):rows.append(cells)
   i+=1
  n=max(map(len,rows)); widths={2:[122,385],3:[132,185,190],4:[110,160,110,127]}.get(n,[507/n]*n)
  data=[[Paragraph(inline(c),st['SmallM']) for c in row]+['']*(n-len(row)) for row in rows]
  table=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
  table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f2f2f2')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#000000'))]))
  story.extend([table,Spacer(1,10)]);continue
 h=re.match(r'^(#{1,3}) (.+)',t)
 if h:story.append(Paragraph(inline(h[2]),st['H'+str(len(h[1]))+'M']));i+=1;continue
 block=[t.lstrip('> ')]
 i+=1
 while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ','**')):
  block.append(lines[i].strip());i+=1
 texto=' '.join(block)
 story.append(Paragraph(inline(texto),st['BodyL' if 'http' in texto else 'BodyM']))
SimpleDocTemplate(str(R/'docs/E0-propuesta.pdf'),pagesize=(595.28,841.89),leftMargin=44,rightMargin=44,topMargin=39,bottomMargin=55,title='MineTrac E0 - Propuesta de negocio',author='Equipo MineTrac').build(story,onFirstPage=foot,onLaterPages=foot)
