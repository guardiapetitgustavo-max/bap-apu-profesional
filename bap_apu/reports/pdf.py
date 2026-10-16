import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from bap_apu.brand import APP_NAME, COMPANY_NAME, TAGLINE, WHATSAPP, EMAIL, WEBSITE, COLOR_NAVY, COLOR_TEAL
from bap_apu.paths import recurso

def exportar_apu_pdf(nombre_proyecto, datos_apu, subtotales, total_general, ruta_guardado):
    """Genera un archivo PDF profesional con el Análisis de Precios Unitarios."""
    
    filename = ruta_guardado
    carpeta_destino = os.path.dirname(os.path.abspath(filename))
    if not os.path.isdir(carpeta_destino):
        raise FileNotFoundError(f"La carpeta de destino no existe: {carpeta_destino}")
    
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    # Estilos de texto
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor(COLOR_NAVY), alignment=1)
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=14)
    table_text = ParagraphStyle('TableText', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11)
    table_header = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=colors.white)

    ruta_logo = str(recurso("assets", "bap_logo_principal.png"))

    try:
        ancho_deseado = 215
        from reportlab.lib.utils import ImageReader
        imagen = ImageReader(ruta_logo)
        ancho_original, alto_original = imagen.getSize()
        alto_proporcional = (ancho_deseado / ancho_original) * alto_original
        
        logo = Image(ruta_logo, width=ancho_deseado, height=alto_proporcional)
        logo.hAlign = 'CENTER'
        story.append(logo)
        story.append(Spacer(1, 15))
    except Exception:
        pass  # sin logo el PDF se genera igual

    # 1. Encabezado del Reporte
    story.append(Paragraph(APP_NAME.upper(), title_style))
    story.append(Paragraph("SISTEMA DE ANÁLISIS DE PRECIOS UNITARIOS", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<b>Proyecto:</b> {nombre_proyecto}", meta_style))
    story.append(Paragraph(f"<b>Moneda:</b> Soles (S/)", meta_style))
    story.append(Spacer(1, 20))

    # 2. Estructura de la Tabla de Datos
    # Columnas: Descripción, Tipo, Unidad, Precio, Cantidad, Parcial
    tabla_datos = [[
        Paragraph("Descripción del Recurso", table_header),
        Paragraph("Tipo", table_header),
        Paragraph("Unidad", table_header),
        Paragraph("Precio (S/)", table_header),
        Paragraph("Cantidad", table_header),
        Paragraph("Parcial (S/)", table_header)
    ]]

    for item in datos_apu:
        # item: (id, nombre, unidad, precio, cantidad, parcial, tipo)
        tabla_datos.append([
            Paragraph(str(item[1]), table_text),
            Paragraph(str(item[6]), table_text),
            Paragraph(str(item[2]), table_text),
            Paragraph(f"{item[3]:.2f}", table_text),
            Paragraph(f"{item[4]:.4f}", table_text),
            Paragraph(f"{item[5]:.2f}", table_text)
        ])

    # Construcción visual de la tabla
    t = Table(tabla_datos, colWidths=[200, 80, 50, 60, 60, 75])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLOR_NAVY)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # 3. Bloque Resumen de Totales
    resumen_datos = [
        [Paragraph("<b>RESUMEN ECONÓMICO</b>", table_header), ""],
        [Paragraph("Mano de Obra:", meta_style), Paragraph(f"S/ {subtotales.get('Mano de Obra', 0):.2f}", meta_style)],
        [Paragraph("Materiales:", meta_style), Paragraph(f"S/ {subtotales.get('Materiales', 0):.2f}", meta_style)],
        [Paragraph("Equipo / Herramientas:", meta_style), Paragraph(f"S/ {subtotales.get('Equipo', 0):.2f}", meta_style)],
        [Paragraph("<b>COSTO TOTAL DIRECTO:</b>", meta_style), Paragraph(f"<b>S/ {total_general:.2f}</b>", meta_style)]
    ]
    
    t_resumen = Table(resumen_datos, colWidths=[150, 100])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COLOR_NAVY)),
        ('SPAN', (0, 0), (1, 0)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#aaaaaa")),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e8f5e9")), # Resaltado verde al total
    ]))
    
    # Alinear resumen a la derecha
    t_resumen_container = Table([[ "", t_resumen]], colWidths=[275, 250])
    story.append(t_resumen_container)
    story.append(Spacer(1, 18))
    pie_style = ParagraphStyle('PieBAP', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor(COLOR_TEAL), alignment=1)
    story.append(Paragraph(f"{COMPANY_NAME} | {TAGLINE}", pie_style))
    story.append(Paragraph(f"WhatsApp: {WHATSAPP} | {EMAIL}", pie_style))
    story.append(Paragraph(WEBSITE, pie_style))

    doc.build(story)

