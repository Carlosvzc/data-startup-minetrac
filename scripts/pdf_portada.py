"""Preparamos la portada de E0 y E1 con los datos del equipo."""
from reportlab.platypus import Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

def portada(entrega, regular, bold):
    title=ParagraphStyle('PortadaTitulo'+entrega,fontName=bold,fontSize=27,leading=34,textColor=colors.black,spaceAfter=18)
    body=ParagraphStyle('PortadaCuerpo'+entrega,fontName=regular,fontSize=11,leading=17,textColor=colors.black,spaceAfter=12)
    section=ParagraphStyle('PortadaSeccion'+entrega,parent=body,fontName=bold,spaceBefore=10,spaceAfter=5)
    out=[Spacer(1,28),Paragraph('MineTrac',title),
         Paragraph('Proyecto Integrador Data Startup',body),
         Paragraph(entrega+' | '+('Propuesta de negocio' if entrega=='E0' else 'Dashboard empresarial'),section),
         Paragraph('26 de octubre de 2026',body),
         Paragraph('Proyecto',section),Paragraph('MineTrac (data-startup-minetrac)',body),
         Paragraph('Institución y carrera',section),
         Paragraph('Tecnológico Nacional de México, campus Colima<br/>Ingeniería en Inteligencia Artificial',body),
         Paragraph('Asignaturas y docentes',section),
         Paragraph('Analítica de Datos (IAD-2403)<br/>Mtro. Armando Román Gallardo Heredia',body),
         Paragraph('Cómputo en la Nube (IAD-2408)<br/>Mtro. Mónico Sánchez Velasco',body),
         Paragraph('Cliente',section),Paragraph('Máquinas Centella S.A. de C.V.',body),
         Paragraph('Integrantes',section),
         Paragraph('Carlos Alejandro Vizcaino Anguiano<br/>Cloud Lead, matrícula 25460343',body),
         Paragraph('Diego Reyes Natilla<br/>Data Lead, matrícula 25460331',body),
         PageBreak()]
    return out
