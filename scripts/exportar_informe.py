
from pathlib import Path
import html,re,base64,sys
from pdf_portada import portada
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT,TA_JUSTIFY
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[1]
ENTREGA=sys.argv[1] if len(sys.argv)>1 else 'E1'
FUENTE={'E1':'E1-dashboard.md','E2':'E2-informe.md','E3':'E3-modelos.md'}[ENTREGA]
TITULO={'E1':'Dashboard empresarial','E2':'Cimientos en la nube','E3':'Inteligencia en producción'}[ENTREGA]
INCRUSTAR={'E1':('evidencias/tablero/','evidencias/iam_rol'),'E2':('evidencias/e2/','arquitectura_e2'),'E3':('evidencias/e3/','arquitectura_e2')}[ENTREGA]
def buscar_fuente(candidatas):
    for c in candidatas:
        if Path(c).exists():
            return c
    raise SystemExit('No encontramos Arial ni una fuente equivalente: '+', '.join(candidatas))
# Arial en Windows; en Linux usamos Liberation Sans, que tiene las mismas medidas que Arial.
for nombre, rutas in [('Arial', ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']),
                      ('ArialBold', ['C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'])]:
    pdfmetrics.registerFont(TTFont(nombre, buscar_fuente(rutas)))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='ArialBold',italic='Arial',boldItalic='ArialBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyX',fontName='Arial',alignment=TA_JUSTIFY,fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#000000')))
styles.add(ParagraphStyle(name='BodyL',fontName='Arial',alignment=TA_LEFT,fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#000000')))
styles.add(ParagraphStyle(name='TitleX',fontName='ArialBold',fontSize=25,leading=31,spaceAfter=20,textColor=colors.HexColor('#000000')))
styles.add(ParagraphStyle(name='H2X',fontName='ArialBold',fontSize=15,leading=19,spaceBefore=16,spaceAfter=10,keepWithNext=True,textColor=colors.HexColor('#000000')))
styles.add(ParagraphStyle(name='H3X',fontName='ArialBold',fontSize=11,leading=15,spaceBefore=12,spaceAfter=8,keepWithNext=True,textColor=colors.black))
blocks=(ROOT/'docs'/FUENTE).read_text(encoding='utf-8').split('\n\n')
story=portada(ENTREGA,'Arial','ArialBold');web=[]
for b in blocks:
 b=b.strip()
 if not b: continue
 if b.startswith('!['):
  rel=b.split('](')[1][:-1];path=ROOT/'docs'/rel
  if not rel.startswith(INCRUSTAR):
   story.append(Paragraph('Consultamos esta captura en el repositorio: '+html.escape(rel),styles['BodyX']))
   continue
  from PIL import Image as PILImage
  iw,ih=PILImage.open(path).size
  ancho=min(475,640*iw/ih);img=Image(str(path),width=ancho,height=ancho*ih/iw);img.keepWithNext=True;gap=Spacer(1,10);gap.keepWithNext=True;story.extend([img,gap])
  web.append('<img src="data:image/'+('jpeg' if path.suffix.lower()=='.jpg' else 'png')+';base64,'+base64.b64encode(path.read_bytes()).decode()+'" alt="Gráfica">')
 else:
  level=1 if b.startswith('# ') else 2 if b.startswith('## ') else 3 if b.startswith('### ') else 0
  text=b[level+1:] if level else b
  style=styles['TitleX' if level==1 else 'H2X' if level==2 else 'H3X' if level==3 else 'BodyL' if 'http' in text else 'BodyX']
  story.append(Paragraph(re.sub(r'(https?://[^\s)]*[^\s).;,])',r'<a href="\1" color="#000000"><u>\1</u></a>',html.escape(text)),style))
  tag='h'+str(level) if level else 'p'
  web.append('<'+tag+'>'+html.escape(text)+'</'+tag+'>')
def foot(c,d):
 c.setStrokeColor(colors.HexColor('#000000'));c.line(42,39,552,39)
 c.setFont('Arial',8);c.setFillColor(colors.HexColor('#000000'))
 c.drawString(42,26,'MineTrac · '+ENTREGA)
 c.drawRightString(552,26,str(d.page))
doc=SimpleDocTemplate(str(ROOT/('docs/'+ENTREGA+'-informe.pdf')),pagesize=(595.28,841.89),leftMargin=47,rightMargin=47,topMargin=42,bottomMargin=55,title='MineTrac '+ENTREGA+' - '+TITULO,author='Equipo MineTrac')
doc.build(story,onFirstPage=foot,onLaterPages=foot)
print('PDF creado en docs/'+ENTREGA+'-informe.pdf')



