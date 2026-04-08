import streamlit as st
from fpdf import FPDF
import datetime
import io
import tempfile
from streamlit_drawable_canvas import st_canvas
import numpy as np
from PIL import Image

# ========= Pie de página =========
FOOTER_LINES = [
    "PAUTA MANTENIMIENTO PREVENTIVO INCUBADORA (Ver 2)",
    "UNIDAD DE INGENIERÍA CLÍNICA",
    "HOSPITAL REGIONAL DE TALCA",
]

class PDF(FPDF):
    def __init__(self, *args, footer_lines=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._footer_lines = footer_lines or []

    def footer(self):
        if not self._footer_lines:
            return
        self.set_y(-15)
        y = self.get_y()
        subtitle_fs = 6.2
        line_h = 3.4
        first_line = self._footer_lines[0]
        self.set_font("Arial", "B", subtitle_fs)
        text_w = self.get_string_width(first_line)
        x_left = self.l_margin
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.2)
        self.line(x_left, y, x_left + text_w, y)
        self.ln(1.6)
        self.set_x(self.l_margin)
        self.cell(0, line_h, first_line, ln=1, align="L")
        self.set_font("Arial", "", subtitle_fs)
        for line in self._footer_lines[1:]:
            self.set_x(self.l_margin)
            self.cell(0, line_h, line, ln=1, align="L")

# ========= utilidades =========
def _crop_signature(canvas_result):
    if canvas_result.image_data is None:
        return None
    img_array = canvas_result.image_data.astype(np.uint8)
    img = Image.fromarray(img_array)
    gray_img = img.convert('L')
    threshold = 230
    coords = np.argwhere(np.array(gray_img) < threshold)
    if coords.size == 0:
        return None
    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)
    cropped_img = img.crop((min_x, min_y, max_x + 1, max_y + 1))
    if cropped_img.mode == 'RGBA':
        cropped_img = cropped_img.convert('RGB')
    img_byte_arr = io.BytesIO()
    cropped_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def add_signature_inline(pdf_obj, canvas_result, target_x_center, y, max_w=50, max_h=18):
    """Añade la firma centrada en target_x_center"""
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w, img_h = img.size
        # Calcular proporciones
        aspect = img_h / img_w
        final_w = max_w
        final_h = final_w * aspect
        
        if final_h > max_h:
            final_h = max_h
            final_w = final_h / aspect
        
        # Centrar horizontalmente respecto al punto dado
        pos_x = target_x_center - (final_w / 2)
        # Ajustar y para que la firma quede sobre la línea
        pos_y = y - final_h 
        
        pdf_obj.image(tmp_path, x=pos_x, y=pos_y, w=final_w, h=final_h)
    except Exception as e:
        st.error(f"Error al añadir imagen: {e}")

def draw_si_no_boxes(pdf, x, y, selected, size=4.5, gap=4, text_gap=1.5, label_w=36):
    pdf.set_font("Arial", "", 7.5)
    pdf.set_xy(x, y)
    pdf.cell(label_w, size, "EQUIPO OPERATIVO:", 0, 0)
    x_box_si = x + label_w + 2
    pdf.rect(x_box_si, y, size, size)
    pdf.set_xy(x_box_si, y); pdf.cell(size, size, "X" if selected == "SI" else "", 0, 0, "C")
    pdf.set_xy(x_box_si + size + text_gap, y); pdf.cell(6, size, "SI", 0, 0)
    x_box_no = x_box_si + size + text_gap + 6 + gap
    pdf.rect(x_box_no, y, size, size)
    pdf.set_xy(x_box_no, y); pdf.cell(size, size, "X" if selected == "NO" else "", 0, 0, "C")
    pdf.set_xy(x_box_no + size + text_gap, y); pdf.cell(6, size, "NO", 0, 1)

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w,
                          row_h=3.4, head_fs=7.2, cell_fs=6.2,
                          indent_w=5.0, title_tab_spaces=2):
    title_prefix = " " * (title_tab_spaces * 2)
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230); pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", head_fs)
    pdf.cell(item_w, row_h, f"{title_prefix}{section_title}", border=1, ln=0, align="L", fill=True)
    pdf.set_font("Arial", "B", cell_fs)
    pdf.cell(col_w, row_h, "OK",  border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO",  border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)

    pdf.set_font("Arial", "", cell_fs)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(indent_w, row_h, "", border=0, ln=0)
        pdf.cell(max(1, item_w - indent_w), row_h, item, border=0, ln=0, align="L")
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, ln=0, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, ln=1, align="C")
    pdf.ln(1.6)

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text,
                          head_h=4.6, fs_head=7.2, fs_body=7.0,
                          body_line_h=3.2, padding=1.2):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230); pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", fs_head)
    pdf.cell(w, head_h, title, border=1, ln=1, align="L", fill=True)

    y_body = y + head_h
    x_text = x + padding
    w_text = max(1, w - 2*padding)
    pdf.set_xy(x_text, y_body + padding)
    pdf.set_font("Arial", "", fs_body)
    if text:
        pdf.multi_cell(w_text, body_line_h, text, border=0, align="L")

    end_y = pdf.get_y()
    content_h = max(min_h, (end_y - (y_body + padding)) + padding)
    pdf.rect(x, y_body, w, content_h)
    pdf.set_y(y_body + content_h)

def draw_analisis_columns(pdf, x_start, y_start, col_w, data_list):
    row_h_field = 3.4
    label_w = 28.0
    text_w = col_w - label_w - 3.0
    TAB = "  " * 2
    
    def draw_column_no_lines(x, y, data):
        yy = y
        def field(lbl, val=""):
            nonlocal yy
            pdf.set_xy(x, yy); pdf.set_font("Arial", "", 6.2)
            pdf.cell(label_w, row_h_field, f"{TAB}{lbl}", border=0, ln=0)
            pdf.set_xy(x + label_w + 2, yy)
            pdf.cell(text_w, row_h_field, f": {val}", border=0, ln=1)
            yy += row_h_field
        field("EQUIPO",  data.get('equipo', ''))
        field("MARCA",   data.get('marca', ''))
        field("MODELO",  data.get('modelo', ''))
        field("NÚMERO SERIE", data.get('serie', ''))
        return yy
    
    num_equipos = len(data_list)
    y_current = y_start
    
    if num_equipos == 1:
        draw_column_no_lines(x_start, y_current, data_list[0])
        y_current = pdf.get_y() + 2
    elif num_equipos >= 2:
        gap_cols = 6
        col_w2 = (col_w - gap_cols) / 2.0
        left_x = x_start
        right_x = x_start + col_w2 + gap_cols
        
        end_left = draw_column_no_lines(left_x, y_current, data_list[0])
        end_right = draw_column_no_lines(right_x, y_current, data_list[1])
        y_current = max(end_left, end_right) + 2

    if num_equipos >= 3:
        gap_cols = 6
        col_w2 = (col_w - gap_cols) / 2.0
        left_x = x_start
        right_x = x_start + col_w2 + gap_cols
        
        end_left_row2 = draw_column_no_lines(left_x, y_current, data_list[2])
        end_right_row2 = 0
        if num_equipos >= 4:
            end_right_row2 = draw_column_no_lines(right_x, y_current, data_list[3])
        y_current = max(end_left_row2, end_right_row2) + 2
    
    return y_current

# ========= app =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Incubadora")

    # --- CAMPOS DE ENTRADA ---
    ideq = st.text_input("IDEQ")
    marca = st.text_input("MARCA")
    modelo = st.text_input("MODELO")
    sn = st.text_input("NÚMERO DE SERIE")
    inventario = st.text_input("N/INVENTARIO")
    fecha = st.date_input("FECHA", value=datetime.date.today())
    ubicacion = st.text_input("UBICACIÓN")

    def checklist(title, items):
        st.subheader(title)
        respuestas = []
        for item in items:
            col1, col2 = st.columns([5, 3])
            with col1:
                st.markdown(item)
            with col2:
                seleccion = st.radio("", ["OK", "NO", "N/A"],
                                     horizontal=True, key=item)
            respuestas.append((item, seleccion))
        return respuestas

    chequeo_visual = checklist("1. Chequeo visual", ["1.1. Ruedas", "1.2. Gabinetes", "1.3. Cable de poder", "1.4. Puerta"])
    grupo_motor = checklist("2. Grupo motor", ["2.1. Interruptor de poder", "2.2. Test de encendido", "2.3. Funciones de panel de control operativas", "2.4. Control modo aire operativo", "2.5. Calibración de temperatura aire (+/- 0.2)", "2.6. Motor/Aspa", "2.7. Alarma"])
    cuerpo = checklist("3. Cuerpo", ["3.1. Bacinete / bandejas", "3.2. Empaquetaduras", "3.3. Estanque humedad", "3.4. Microfiltro de aire", "3.5. Seguro de cúpula", "3.6. Mástil IV"])
    cupula = checklist("4. Cúpula", ["4.1. Cúpula sin trizaduras", "4.2. Puertas de acceso", "4.3. Aros iris", "4.4. Pestillos"])
    seguridad_electrica = checklist("5. Seguridad eléctrica", ["5.1. Medición de corrientes de fuga normal condición", "5.2. Medición de corrientes de fuga con neutro abierto"])

    st.subheader("6. Instrumentos de análisis")
    if "analisis_equipos" not in st.session_state:
        st.session_state.analisis_equipos = [{}, {}]

    def add_equipo():
        st.session_state.analisis_equipos.append({})

    for i, _ in enumerate(st.session_state.analisis_equipos):
        st.markdown(f"**Equipo {i+1}**")
        st.session_state.analisis_equipos[i]["equipo"] = st.text_input("Equipo", key=f"equipo_{i}")
        st.session_state.analisis_equipos[i]["marca"] = st.text_input("Marca", key=f"marca_{i}")
        st.session_state.analisis_equipos[i]["modelo"] = st.text_input("Modelo", key=f"modelo_{i}")
        st.session_state.analisis_equipos[i]["serie"] = st.text_input("Número de Serie", key=f"serie_{i}")

    st.button("Agregar Equipo +", on_click=add_equipo)

    observaciones = st.text_area("Observaciones")
    observaciones_interno = st.text_area("Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    col_tecnico, col_ingenieria, col_clinico = st.columns(3)
    with col_tecnico:
        st.write("Técnico Encargado:")
        canvas_result_tecnico = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=150, width=300, drawing_mode="freedraw", key="canvas_tecnico")
    with col_ingenieria:
        st.write("Ingeniería Clínica:")
        canvas_result_ingenieria = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=150, width=300, drawing_mode="freedraw", key="canvas_ingenieria")
    with col_clinico:
        st.write("Personal Clínico:")
        canvas_result_clinico = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=150, width=300, drawing_mode="freedraw", key="canvas_clinico")

    if st.button("Generar PDF"):
        SIDE_MARGIN = 9
        pdf = PDF("L", "mm", "A4", footer_lines=FOOTER_LINES)
        pdf.set_margins(SIDE_MARGIN, 10, SIDE_MARGIN)
        pdf.add_page()

        page_w = pdf.w
        usable_w = page_w - 2 * SIDE_MARGIN
        col_total_w = (usable_w - 6) / 2.0
        SECOND_COL_LEFT = SIDE_MARGIN + col_total_w + 6

        # Encabezado (resumido para el ejemplo)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "PAUTA MANTENCIÓN INCUBADORA", 0, 1, "C")

        # Datos equipo
        pdf.set_font("Arial", "", 8)
        pdf.cell(35, 5, "MARCA:", 0, 0); pdf.cell(0, 5, marca, 0, 1)
        pdf.cell(35, 5, "MODELO:", 0, 0); pdf.cell(0, 5, modelo, 0, 1)
        pdf.cell(35, 5, "NÚMERO DE SERIE:", 0, 0); pdf.cell(0, 5, sn, 0, 1)
        pdf.ln(5)

        # Simulación de posición para firmas
        pdf.set_y(140) 
        y_firmas_base = pdf.get_y()
        
        # --- Configuración de Recepción Conforme ---
        # Definimos los anchos de las líneas
        line_w = 50
        # Centros de las dos columnas de firma
        center_f1 = SECOND_COL_LEFT + (col_total_w / 4)
        center_f2 = SECOND_COL_LEFT + (3 * col_total_w / 4)
        
        # Dibujar Imágenes Centradas sobre la línea
        add_signature_inline(pdf, canvas_result_ingenieria, center_f1, y_firmas_base, max_w=line_w)
        add_signature_inline(pdf, canvas_result_clinico, center_f2, y_firmas_base, max_w=line_w)

        # Dibujar las líneas de firma
        pdf.set_draw_color(0, 0, 0)
        pdf.line(center_f1 - (line_w/2), y_firmas_base, center_f1 + (line_w/2), y_firmas_base)
        pdf.line(center_f2 - (line_w/2), y_firmas_base, center_f2 + (line_w/2), y_firmas_base)
        
        # Texto debajo de las líneas
        pdf.set_font("Arial", "B", 6.5)
        pdf.set_xy(center_f1 - (line_w/2), y_firmas_base + 1)
        pdf.multi_cell(line_w, 3, "RECEPCIÓN CONFORME\nPERSONAL INGENIERÍA CLÍNICA", 0, "C")
        
        pdf.set_xy(center_f2 - (line_w/2), y_firmas_base + 1)
        pdf.multi_cell(line_w, 3, "RECEPCIÓN CONFORME\nPERSONAL CLÍNICO", 0, "C")

        out = pdf.output(dest="S")
        st.download_button("Descargar PDF", bytes(out) if not isinstance(out, str) else out.encode("latin1"), file_name=f"Mantenimiento_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()
