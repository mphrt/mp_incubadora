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

def add_signature_inline(pdf_obj, canvas_result, x, y, w_mm=65, h_mm=20, center_on_w=None):
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w = w_mm
        img_h = (img.height / img.width) * img_w
        if img_h > h_mm:
            img_h = h_mm
            img_w = (img.width / img.height) * img_h
        
        final_x = x
        if center_on_w:
            final_x = x + (center_on_w - img_w) / 2
            
        pdf_obj.image(tmp_path, x=final_x, y=y, w=img_w, h=img_h)
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

    # --- Configuración de Marcas ---
    marcas_base = ["DRAGER AIRSHIELD", "GENERAL ELECTRIC", "MEDIX", "FANEM"]
    marcas_base.sort() 
    opciones_marca = [""] + marcas_base + ["+ Añadir nueva marca"]

    ideq = st.text_input("IDEQ")
    
    # Menú desplegable para MARCA
    seleccion_marca = st.selectbox("MARCA", opciones_marca, index=0)
    if seleccion_marca == "+ Añadir nueva marca":
        marca = st.text_input("Escribe el nombre de la nueva marca")
    else:
        marca = seleccion_marca

    modelo = st.text_input("MODELO")
    sn = st.text_input("NÚMERO DE SERIE")
    inventario = st.text_input("NÚMERO DE INVENTARIO")
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

    chequeo_visual = checklist(
        "1. Chequeo visual (estado de componentes)",
        ["1.1. Ruedas", "1.2. Gabinetes", "1.3. Cable de poder", "1.4. Puerta"]
    )
    grupo_motor = checklist(
        "2. Grupo motor",
        ["2.1. Interruptor de poder", "2.2. Test de encendido", "2.3. Funciones de panel de control operativas", "2.4. Control modo aire operativo", "2.5. Calibración de temperatura aire (+/- 0.2)", "2.6. Motor/Aspa", "2.7. Alarma"]
    )
    cuerpo = checklist(
        "3. Cuerpo",
        ["3.1. Bacinete / bandejas", "3.2. Empaquetaduras", "3.3. Estanque humedad", "3.4. Microfiltro de aire", "3.5. Seguro de cúpula", "3.6. Mástil IV"]
    )
    cupula = checklist(
        "4. Cúpula",
        ["4.1. Cúpula sin trizaduras", "4.2. Puertas de acceso", "4.3. Aros iris", "4.4. Pestillos"]
    )
    seguridad_electrica = checklist(
        "5. Seguridad eléctrica",
        ["5.1. Medición de corrientes de fuga normal condición", "5.2. Medición de corrientes de fuga con neutro abierto"]
    )

    st.subheader("6. Instrumentos de análisis")
    if "analisis_equipos" not in st.session_state:
        st.session_state.analisis_equipos = [{}, {}]

    def add_equipo():
        st.session_state.analisis_equipos.append({})

    for i, _ in enumerate(st.session_state.analisis_equipos):
        st.markdown(f"**Equipo {i+1}**")
        col_eq, col_btn = st.columns([0.9, 0.1])
        with col_eq:
            st.session_state.analisis_equipos[i]["equipo"] = st.text_input("Equipo", key=f"equipo_{i}")
            st.session_state.analisis_equipos[i]["marca"] = st.text_input("Marca", key=f"marca_{i}")
            st.session_state.analisis_equipos[i]["modelo"] = st.text_input("Modelo", key=f"modelo_{i}")
            st.session_state.analisis_equipos[i]["serie"] = st.text_input("Número de Serie", key=f"serie_{i}")
        if i > 0:
            with col_btn:
                st.write("")
                if st.button("−", key=f"remove_btn_{i}"):
                    st.session_state.analisis_equipos.pop(i)
                    st.rerun()
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
        canvas_result_tecnico = st_canvas(fill_color="rgba(255,165,0,0.3)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=190, width=360, drawing_mode="freedraw", key="canvas_tecnico")
    with col_ingenieria:
        st.write("Ingeniería Clínica:")
        canvas_result_ingenieria = st_canvas(fill_color="rgba(255,165,0,0.3)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=190, width=360, drawing_mode="freedraw", key="canvas_ingenieria")
    with col_clinico:
        st.write("Personal Clínico:")
        canvas_result_clinico = st_canvas(fill_color="rgba(255,165,0,0.3)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=190, width=360, drawing_mode="freedraw", key="canvas_clinico")

    if st.button("Generar PDF"):
        if not marca or marca == "":
            st.error("Por favor, seleccione o ingrese una marca.")
            return

        SIDE_MARGIN = 9
        TOP_MARGIN = 4

        pdf = PDF("L", "mm", "A4", footer_lines=FOOTER_LINES)
        pdf.set_margins(SIDE_MARGIN, TOP_MARGIN, SIDE_MARGIN)
        pdf.set_auto_page_break(True, margin=TOP_MARGIN + 8)
        pdf.add_page()

        page_w = pdf.w
        COL_GAP = 6
        FIRST_COL_LEFT = SIDE_MARGIN
        usable_w = page_w - 2 * SIDE_MARGIN
        col_total_w = (usable_w - COL_GAP) / 2.0
        COL_W = 12.0
        ITEM_W = max(62.0, col_total_w - 3 * COL_W)
        FIRST_TAB_RIGHT = FIRST_COL_LEFT + col_total_w
        SECOND_COL_LEFT = FIRST_TAB_RIGHT + COL_GAP

        # ======= ENCABEZADO =======
        logo_x, logo_y = 2, 2
        LOGO_W_MM = 60
        sep = 4
        title_text = "PAUTA MANTENCIÓN INCUBADORA"

        try:
            pdf.image("logo_hrt_final.jpg", x=logo_x, y=logo_y, w=LOGO_W_MM)
            with Image.open("logo_hrt_final.jpg") as im:
                logo_h = LOGO_W_MM * (im.height / im.width)
        except:
            logo_h = LOGO_W_MM * 0.8

        # Recuadro IDEQ
        pdf.set_font("Arial", "B", 7.5)
        ideq_label = f"IDEQ: {ideq}"
        ideq_w = pdf.get_string_width(ideq_label) + 6
        pdf.set_xy(page_w - SIDE_MARGIN - ideq_w, logo_y)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(ideq_w, 5, ideq_label, border=1, ln=0, align="C", fill=True)

        # Título Pauta
        pdf.set_font("Arial", "B", 7)
        title_x = logo_x + LOGO_W_MM + sep
        title_y = (logo_y + logo_h) - 5.0
        pdf.set_xy(title_x, title_y)
        pdf.cell(FIRST_TAB_RIGHT - title_x, 5.0, title_text, border=1, ln=1, align="C", fill=True)

        header_bottom = max(logo_y + logo_h, title_y + 5.0)
        pdf.set_y(header_bottom + 2)

        # ======= COLUMNA IZQUIERDA – datos equipo =======
        pdf.set_font("Arial", "", 7.5)
        line_h = 3.4
        label_w = 35.0
        y_ini = pdf.get_y()
        
        # Fecha
        x_date = FIRST_TAB_RIGHT - 33.0
        pdf.set_xy(x_date - 15, y_ini)
        pdf.set_font("Arial", "B", 7.5); pdf.cell(13, line_h, "FECHA:", 0, 0, "R"); pdf.set_font("Arial", "", 7.5)
        pdf.set_xy(x_date, y_ini)
        pdf.cell(11, line_h, f"{fecha.day:02d}", 1, 0, "C")
        pdf.cell(11, line_h, f"{fecha.month:02d}", 1, 0, "C")
        pdf.cell(11, line_h, f"{fecha.year:04d}", 1, 1, "C")

        # Datos
        def l_field(lbl, val):
            pdf.set_x(FIRST_COL_LEFT)
            pdf.cell(label_w, line_h, f"{lbl}", 0, 0, "L")
            pdf.cell(2, line_h, ":", 0, 0, "C")
            pdf.cell(0, line_h, f"{val}", 0, 1, "L")

        pdf.set_y(y_ini)
        l_field("MARCA", marca)
        l_field("MODELO", modelo)
        l_field("S/N", sn)
        l_field("N/INVENTARIO", inventario)
        l_field("UBICACIÓN", ubicacion)

        pdf.ln(2.6)
        create_checkbox_table(pdf, "1. Chequeo visual (estado de componentes)", chequeo_visual, FIRST_COL_LEFT, ITEM_W, COL_W)
        create_checkbox_table(pdf, "2. Grupo motor", grupo_motor, FIRST_COL_LEFT, ITEM_W, COL_W)
        create_checkbox_table(pdf, "3. Cuerpo", cuerpo, FIRST_COL_LEFT, ITEM_W, COL_W)
        create_checkbox_table(pdf, "4. Cúpula", cupula, FIRST_COL_LEFT, ITEM_W, COL_W)
        create_checkbox_table(pdf, "5. Seguridad eléctrica", seguridad_electrica, FIRST_COL_LEFT, ITEM_W, COL_W)

        # ======= COLUMNA DERECHA =======
        pdf.set_y(header_bottom + 2)
        pdf.set_x(SECOND_COL_LEFT)
        pdf.set_font("Arial", "B", 7.5)
        pdf.cell(col_total_w, 4.0, "  6. Instrumentos de análisis", border=1, ln=1, fill=True)
        y_bot_an = draw_analisis_columns(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, st.session_state.analisis_equipos)
        
        pdf.set_y(y_bot_an)
        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 10, "  Observaciones", observaciones)
        pdf.ln(2)
        draw_si_no_boxes(pdf, SECOND_COL_LEFT, pdf.get_y(), operativo, size=4.5, label_w=40)
        pdf.ln(2)

        # Técnico y Firma
        pdf.set_x(SECOND_COL_LEFT); pdf.set_font("Arial", "", 7.5)
        pdf.cell(0, 4.0, f"NOMBRE TÉCNICO/INGENIERO: {tecnico}", 0, 1)
        y_sig_tec = pdf.get_y() + 1
        pdf.set_x(SECOND_COL_LEFT); pdf.cell(14, 4.0, "FIRMA:", 0, 0)
        add_signature_inline(pdf, canvas_result_tecnico, x=pdf.get_x() + 2, y=y_sig_tec, w_mm=50, h_mm=12)
        
        pdf.set_y(y_sig_tec + 14)
        pdf.set_x(SECOND_COL_LEFT)
        pdf.cell(0, 4.0, f"EMPRESA RESPONSABLE: {empresa}", 0, 1)
        pdf.ln(2.0)

        draw_boxed_text_auto(pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, 10, "  Observaciones (uso interno)", observaciones_interno)
        pdf.ln(4)

        # Firmas Recepción
        y_recep = pdf.get_y()
        w_half = col_total_w / 2
        add_signature_inline(pdf, canvas_result_ingenieria, x=SECOND_COL_LEFT + 5, y=y_recep, w_mm=40, h_mm=10, center_on_w=w_half - 10)
        add_signature_inline(pdf, canvas_result_clinico, x=SECOND_COL_LEFT + w_half + 5, y=y_recep, w_mm=40, h_mm=10, center_on_w=w_half - 10)
        
        y_l = y_recep + 11
        pdf.set_draw_color(0,0,0)
        pdf.line(SECOND_COL_LEFT + 5, y_l, SECOND_COL_LEFT + w_half - 5, y_l)
        pdf.line(SECOND_COL_LEFT + w_half + 5, y_l, SECOND_COL_LEFT + col_total_w - 5, y_l)
        
        pdf.set_font("Arial", "B", 6)
        pdf.set_xy(SECOND_COL_LEFT + 5, y_l + 1)
        pdf.multi_cell(w_half - 10, 2.5, "RECEPCIÓN CONFORME\nPERSONAL INGENIERÍA CLÍNICA", 0, 'C')
        pdf.set_xy(SECOND_COL_LEFT + w_half + 5, y_l + 1)
        pdf.multi_cell(w_half - 10, 2.5, "RECEPCIÓN CONFORME\nPERSONAL CLÍNICO", 0, 'C')

        # Generar
        out = pdf.output(dest="S")
        res = bytes(out) if not isinstance(out, str) else out.encode("latin1")
        st.download_button("Descargar PDF", res, file_name=f"IDEQ_MP_Incubadora_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()
