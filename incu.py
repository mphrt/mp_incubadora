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

def add_signature_inline(pdf_obj, canvas_result, x, y, w_mm=65, h_mm=20):
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
        pdf_obj.image(tmp_path, x=x, y=y, w=img_w, h=img_h)
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

    marca = st.text_input("MARCA")
    modelo = st.text_input("MODELO")
    sn = st.text_input("S/N")
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

    # Secciones según la pauta de incubadora
    chequeo_visual = checklist(
        "1.     Chequeo visual (estado de componentes)",
        [
            "1.1.           Ruedas",
            "1.2.           Gabinetes",
            "1.3.           Cable de poder",
            "1.4.           Puerta",
        ],
    )
    grupo_motor = checklist(
        "2.     Grupo motor",
        [
            "2.1.           Interruptor de poder",
            "2.2.           Test de encendido",
            "2.3.           Funciones de panel de control operativas",
            "2.4.           Control modo aire operativo",
            "2.5.           Calibración de temperatura aire (+/- 0.2)",
            "2.6.           Motor/Aspa",
            "2.7.           Alarma",
        ],
    )
    cuerpo = checklist(
        "3.     Cuerpo",
        [
            "3.1.           Bacinete / bandejas",
            "3.2.           Empaquetaduras",
            "3.3.           Estanque humedad",
            "3.4.           Microfiltro de aire",
            "3.5.           Seguro de cúpula",
            "3.6.           Mástil IV",
        ],
    )
    cupula = checklist(
        "4.     Cúpula",
        [
            "4.1.           Cúpula sin trizaduras",
            "4.2.           Puertas de acceso",
            "4.3.           Aros iris",
            "4.4.           Pestillos",
        ],
    )
    seguridad_electrica = checklist(
        "5.     Seguridad eléctrica",
        [
            "5.1.           Medición de corrientes de fuga normal condición",
            "5.2.           Medición de corrientes de fuga con neutro abierto",
        ],
    )

    st.subheader("    6. Instrumentos de análisis")
    if "analisis_equipos" not in st.session_state:
        # por defecto dos equipos, como en la pauta
        st.session_state.analisis_equipos = [{}, {}]

    def add_equipo():
        st.session_state.analisis_equipos.append({})

    for i, _ in enumerate(st.session_state.analisis_equipos):
        st.markdown(f"**Equipo {i+1}**")
        col_eq, col_btn = st.columns([0.9, 0.1])
        with col_eq:
            st.session_state.analisis_equipos[i]["equipo"] = st.text_input(
                "Equipo", key=f"equipo_{i}"
            )
            st.session_state.analisis_equipos[i]["marca"] = st.text_input(
                "Marca", key=f"marca_{i}"
            )
            st.session_state.analisis_equipos[i]["modelo"] = st.text_input(
                "Modelo", key=f"modelo_{i}"
            )
            st.session_state.analisis_equipos[i]["serie"] = st.text_input(
                "Número de Serie", key=f"serie_{i}"
            )
        if i > 0:
            with col_btn:
                st.write("")
                if st.button("−", key=f"remove_btn_{i}"):
                    st.session_state.analisis_equipos.pop(i)
                    st.experimental_rerun()
    st.button("Agregar Equipo +", on_click=add_equipo)

    observaciones = st.text_area("    Observaciones")
    observaciones_interno = st.text_area("    Observaciones (uso interno)")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    st.subheader("Firmas")
    col_tecnico, col_ingenieria, col_clinico = st.columns(3)
    with col_tecnico:
        st.write("Técnico Encargado:")
        canvas_result_tecnico = st_canvas(
            fill_color="rgba(255,165,0,0.3)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#EEEEEE",
            height=190,
            width=360,
            drawing_mode="freedraw",
            key="canvas_tecnico",
        )
    with col_ingenieria:
        st.write("Ingeniería Clínica:")
        canvas_result_ingenieria = st_canvas(
            fill_color="rgba(255,165,0,0.3)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#EEEEEE",
            height=190,
            width=360,
            drawing_mode="freedraw",
            key="canvas_ingenieria",
        )
    with col_clinico:
        st.write("Personal Clínico:")
        canvas_result_clinico = st_canvas(
            fill_color="rgba(255,165,0,0.3)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#EEEEEE",
            height=190,
            width=360,
            drawing_mode="freedraw",
            key="canvas_clinico",
        )

    if st.button("Generar PDF"):
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
            with Image.open("logo_hrt_final.jpg") as im:
                ratio = im.height / im.width if im.width else 1.0
            logo_h = LOGO_W_MM * ratio
        except Exception:
            logo_h = LOGO_W_MM * 0.8

        try:
            pdf.image("logo_hrt_final.jpg", x=logo_x, y=logo_y, w=LOGO_W_MM)
        except Exception:
            st.warning(
                "No se pudo cargar el logo. Deja 'logo_hrt_final.jpg' junto al script."
            )

        pdf.set_font("Arial", "B", 7)
        title_h = 5.0
        title_x = logo_x + LOGO_W_MM + sep
        title_y = (logo_y + logo_h) - title_h
        cell_w = max(10, FIRST_TAB_RIGHT - title_x)
        pdf.set_fill_color(230, 230, 230)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(title_x, title_y)
        pdf.cell(cell_w, title_h, title_text, border=1, ln=1, align="C", fill=True)

        header_bottom = max(logo_y + logo_h, title_y + title_h)
        content_y_base = header_bottom + 2
        pdf.set_y(content_y_base)

        # ======= COLUMNA IZQUIERDA – datos equipo =======
        pdf.set_font("Arial", "", 7.5)
        line_h = 3.4

        label_texts = ["MARCA", "MODELO", "S/N", "N/INVENTARIO", "UBICACIÓN"]
        text_widths = [pdf.get_string_width(t) for t in label_texts]
        max_label_text_w = max(text_widths) if text_widths else 28.0

        LABEL_PAD = 4.0
        EXTRA_PUSH = 8.0
        label_w_common = max_label_text_w + LABEL_PAD + EXTRA_PUSH

        COLON_W = 1.8
        GAP_AFTER_COLON = 1.6

        y_marca = pdf.get_y()
        date_col_w = 11.0
        date_table_w = date_col_w * 3
        x_date_right = FIRST_TAB_RIGHT
        x_date = x_date_right - date_table_w
        fecha_label_w = 13.0
        gap_lab_box = 1.8
        x_label_fecha = x_date - fecha_label_w - gap_lab_box

        # MARCA
        pdf.set_xy(FIRST_COL_LEFT, y_marca)
        pdf.cell(label_w_common, line_h, "MARCA", 0, 0, "L")
        pdf.cell(COLON_W, line_h, ":", 0, 0, "C")
        SAFE_GAP_BEFORE_DATE = 2.0
        x_value_start = FIRST_COL_LEFT + label_w_common + COLON_W + GAP_AFTER_COLON
        max_value_right = x_label_fecha - SAFE_GAP_BEFORE_DATE
        value_w_line1 = max(10, max_value_right - x_value_start)
        pdf.cell(value_w_line1, line_h, f"{marca}", 0, 0, "L")

        # FECHA
        pdf.set_xy(x_label_fecha, y_marca)
        pdf.set_font("Arial", "B", 7.5)
        pdf.cell(fecha_label_w, line_h, "FECHA:", 0, 0, "R")
        pdf.set_font("Arial", "", 7.5)
        dd = f"{fecha.day:02d}"
        mm = f"{fecha.month:02d}"
        yyyy = f"{fecha.year:04d}"
        pdf.set_xy(x_date, y_marca)
        pdf.cell(date_col_w, line_h, dd, 1, 0, "C")
        pdf.cell(date_col_w, line_h, mm, 1, 0, "C")
        pdf.cell(date_col_w, line_h, yyyy, 1, 0, "C")
        pdf.ln(line_h)

        def left_field(lbl, val):
            pdf.set_x(FIRST_COL_LEFT)
            pdf.cell(label_w_common, line_h, f"{lbl}", 0, 0, "L")
            pdf.cell(COLON_W, line_h, ":", 0, 0, "C")
            value_w = FIRST_TAB_RIGHT - (
                FIRST_COL_LEFT + label_w_common + COLON_W + GAP_AFTER_COLON
            )
            value_w = max(10, value_w)
            pdf.cell(value_w, line_h, f"{val}", 0, 1, "L")

        left_field("MODELO", modelo)
        left_field("S/N", sn)
        left_field("N/INVENTARIO", inventario)
        left_field("UBICACIÓN", ubicacion)

        pdf.ln(2.6)

        # ======= COLUMNA IZQUIERDA – checklist =======
        LEFT_ROW_H = 3.4
        create_checkbox_table(
            pdf,
            "1. Chequeo visual (estado de componentes)",
            chequeo_visual,
            x_pos=FIRST_COL_LEFT,
            item_w=ITEM_W,
            col_w=COL_W,
            row_h=LEFT_ROW_H,
            head_fs=7.2,
            cell_fs=6.2,
            indent_w=5.0,
            title_tab_spaces=2,
        )
        create_checkbox_table(
            pdf,
            "2. Grupo motor",
            grupo_motor,
            x_pos=FIRST_COL_LEFT,
            item_w=ITEM_W,
            col_w=COL_W,
            row_h=LEFT_ROW_H,
            head_fs=7.2,
            cell_fs=6.2,
            indent_w=5.0,
            title_tab_spaces=2,
        )
        create_checkbox_table(
            pdf,
            "3. Cuerpo",
            cuerpo,
            x_pos=FIRST_COL_LEFT,
            item_w=ITEM_W,
            col_w=COL_W,
            row_h=LEFT_ROW_H,
            head_fs=7.2,
            cell_fs=6.2,
            indent_w=5.0,
            title_tab_spaces=2,
        )
        create_checkbox_table(
            pdf,
            "4. Cúpula",
            cupula,
            x_pos=FIRST_COL_LEFT,
            item_w=ITEM_W,
            col_w=COL_W,
            row_h=LEFT_ROW_H,
            head_fs=7.2,
            cell_fs=6.2,
            indent_w=5.0,
            title_tab_spaces=2,
        )
        create_checkbox_table(
            pdf,
            "5. Seguridad eléctrica",
            seguridad_electrica,
            x_pos=FIRST_COL_LEFT,
            item_w=ITEM_W,
            col_w=COL_W,
            row_h=LEFT_ROW_H,
            head_fs=7.2,
            cell_fs=6.2,
            indent_w=5.0,
            title_tab_spaces=2,
        )

        # ======= COLUMNA DERECHA =======
        pdf.set_y(content_y_base)
        TAB = "  " * 2
        pdf.set_x(SECOND_COL_LEFT)
        pdf.set_fill_color(230, 230, 230)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 7.5)
        pdf.cell(
            col_total_w,
            4.0,
            f"{TAB}6. Instrumentos de análisis",
            border=1,
            ln=1,
            align="L",
            fill=True,
        )
        pdf.ln(1.0)

        y_bottom_analisis = draw_analisis_columns(
            pdf, SECOND_COL_LEFT, pdf.get_y(), col_total_w, st.session_state.analisis_equipos
        )
        pdf.set_y(y_bottom_analisis)

        # Observaciones
        draw_boxed_text_auto(
            pdf,
            x=SECOND_COL_LEFT,
            y=pdf.get_y(),
            w=col_total_w,
            min_h=10,
            title=f"{TAB}Observaciones",
            text=observaciones,
            head_h=4.6,
            fs_head=7.2,
            fs_body=7.0,
            body_line_h=3.2,
            padding=1.2,
        )
        pdf.ln(2)

        # Equipo operativo + Técnico + Empresa
        y_equipo_op = pdf.get_y()
        draw_si_no_boxes(
            pdf,
            x=SECOND_COL_LEFT,
            y=y_equipo_op,
            selected=operativo,
            size=4.5,
            label_w=40,
        )
        pdf.ln(1.6)

        pdf.set_x(SECOND_COL_LEFT)
        pdf.set_font("Arial", "", 7.5)
        y_nombre = pdf.get_y()
        name_text = f"NOMBRE TÉCNICO/INGENIERO: {tecnico}"
        name_box_w = min(100, col_total_w * 0.58)
        pdf.cell(name_box_w, 4.6, name_text, 0, 0, "L")
        pdf.cell(14, 4.6, "FIRMA:", 0, 0, "L")
        x_sig_tecnico = pdf.get_x()
        add_signature_inline(
            pdf,
            canvas_result_tecnico,
            x=x_sig_tecnico,
            y=y_nombre,
            w_mm=65,
            h_mm=20,
        )
        pdf.set_y(y_nombre + 20 + 2)

        pdf.set_x(SECOND_COL_LEFT)
        pdf.cell(0, 4.0, f"EMPRESA RESPONSABLE: {empresa}", 0, 1)
        pdf.ln(2.0)

        # Observaciones (uso interno)
        draw_boxed_text_auto(
            pdf,
            x=SECOND_COL_LEFT,
            y=pdf.get_y(),
            w=col_total_w,
            min_h=10,
            title=f"{TAB}Observaciones (uso interno)",
            text=observaciones_interno,
            head_h=4.6,
            fs_head=7.2,
            fs_body=7.0,
            body_line_h=3.2,
            padding=1.2,
        )
        pdf.ln(2)

        # Firmas recepción
        ancho_area = col_total_w
        center_left = SECOND_COL_LEFT + (ancho_area * 0.25)
        center_right = SECOND_COL_LEFT + (ancho_area * 0.75)

        pdf.set_font("Arial", "B", 7.5)
        w_rc = pdf.get_string_width("RECEPCIÓN CONFORME")
        w_pi = pdf.get_string_width("PERSONAL INGENIERÍA CLÍNICA")
        w_pc = pdf.get_string_width("PERSONAL CLÍNICO")
        text_block_w = max(w_rc, w_pi, w_pc) + 12
        half_w = ancho_area / 2.0
        max_line_len = half_w - 8
        line_len = min(max(text_block_w, 65), max_line_len)

        sig_w = min(65, line_len - 6)
        sig_h = 20

        SIG_OFF_X_LEFT = 15
        SIG_OFF_Y_LEFT = 0
        SIG_OFF_X_RIGHT = 15
        SIG_OFF_Y_RIGHT = 0

        y_top = pdf.get_y()
        y_sig = y_top + 2.0

        x_line_left = center_left - line_len / 2.0
        x_line_right = center_right - line_len / 2.0

        add_signature_inline(
            pdf,
            canvas_result_ingenieria,
            x=center_left - sig_w / 2.0 + SIG_OFF_X_LEFT,
            y=y_sig + SIG_OFF_Y_LEFT,
            w_mm=sig_w,
            h_mm=sig_h,
        )
        add_signature_inline(
            pdf,
            canvas_result_clinico,
            x=center_right - sig_w / 2.0 + SIG_OFF_X_RIGHT,
            y=y_sig + SIG_OFF_Y_RIGHT,
            w_mm=sig_w,
            h_mm=sig_h,
        )

        y_line = y_sig + sig_h + 3.0
        pdf.set_draw_color(0, 0, 0)
        pdf.line(x_line_left, y_line, x_line_left + line_len, y_line)
        pdf.line(x_line_right, y_line, x_line_right + line_len, y_line)

        pdf.set_xy(x_line_left, y_line + 0.8)
        pdf.cell(line_len, 3.6, "RECEPCIÓN CONFORME", 0, 2, "C")
        pdf.set_xy(x_line_left, pdf.get_y())
        pdf.cell(line_len, 3.6, "PERSONAL INGENIERÍA CLÍNICA", 0, 0, "C")

        pdf.set_xy(x_line_right, y_line + 0.8)
        pdf.cell(line_len, 3.6, "RECEPCIÓN CONFORME", 0, 2, "C")
        pdf.set_xy(x_line_right, pdf.get_y())
        pdf.cell(line_len, 3.6, "PERSONAL CLÍNICO", 0, 0, "C")

        pdf.set_y(max(y_line + 7, pdf.get_y()))

        out = pdf.output(dest="S")
        if isinstance(out, str):
            out = out.encode("latin1")
        else:
            out = bytes(out)

        st.download_button(
            "Descargar PDF",
            out,
            file_name=f"MP_Incubadora_{sn}.pdf",
            mime="application/pdf",
        )

if __name__ == "__main__":
    main()
