
from pathlib import Path
import html,re,base64
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[1]
import matplotlib
_dj = Path(matplotlib.get_data_path()) / 'fonts/ttf'
for nombre, win, alt in [('Arial', r'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'), ('ArialBold', r'C:/Windows/Fonts/arialbd.ttf', 'DejaVuSans-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(nombre, win if Path(win).exists() else str(_dj / alt)))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyX',fontName='Arial',fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#273e4a')))
styles.add(ParagraphStyle(name='TitleX',fontName='ArialBold',fontSize=25,leading=31,spaceAfter=20,textColor=colors.HexColor('#165764')))
styles.add(ParagraphStyle(name='H2X',fontName='ArialBold',fontSize=15,leading=19,spaceBefore=16,spaceAfter=10,keepWithNext=True,textColor=colors.HexColor('#165764')))
styles.add(ParagraphStyle(name='H3X',fontName='ArialBold',fontSize=11,leading=15,spaceBefore=12,spaceAfter=8,keepWithNext=True))
blocks=(ROOT/'docs/E1-dashboard.md').read_text(encoding='utf-8').split('\n\n')
story=[];web=[]
for b in blocks:
 b=b.strip()
 if not b: continue
 if b.startswith('!['):
  rel=b.split('](')[1][:-1];path=ROOT/'docs'/rel
  from PIL import Image as PILImage
  iw,ih=PILImage.open(path).size
  img=Image(str(path),width=475,height=475*ih/iw);img.keepWithNext=True;gap=Spacer(1,10);gap.keepWithNext=True;story.extend([img,gap])
  web.append('<img src="data:image/'+('jpeg' if path.suffix.lower()=='.jpg' else 'png')+';base64,'+base64.b64encode(path.read_bytes()).decode()+'" alt="Gráfica">')
 else:
  level=1 if b.startswith('# ') else 2 if b.startswith('## ') else 3 if b.startswith('### ') else 0
  text=b[level+1:] if level else b
  style=styles['TitleX' if level==1 else 'H2X' if level==2 else 'H3X' if level==3 else 'BodyX']
  story.append(Paragraph(html.escape(text),style))
  tag='h'+str(level) if level else 'p'
  web.append('<'+tag+'>'+html.escape(text)+'</'+tag+'>')
def foot(c,d):
 c.setStrokeColor(colors.HexColor('#c9e1e6'));c.line(42,39,552,39)
 c.setFont('Arial',8);c.setFillColor(colors.HexColor('#5c7480'))
 c.drawString(42,26,'MineTrac · E1 · Información real de Máquinas Centella · operación pendiente')
 c.drawRightString(552,26,str(d.page))
doc=SimpleDocTemplate(str(ROOT/'docs/E1-informe.pdf'),pagesize=(595.28,841.89),leftMargin=47,rightMargin=47,topMargin=42,bottomMargin=55,title='MineTrac E1 - Dashboard empresarial',author='Equipo MineTrac')
doc.build(story,onFirstPage=foot,onLaterPages=foot)
print('PDF creado en docs/E1-informe.pdf')



