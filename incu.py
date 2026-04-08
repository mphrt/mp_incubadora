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

def add_signature_centered(pdf_obj, canvas_result, x_center, y_bottom, w_max=60, h_max=20):
    """Añade la firma centrada sobre un punto X, apoyada en un punto Y (base)"""
    img_byte_arr = _crop_signature(canvas_result)
    if not img_byte_arr:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(img_byte_arr.read())
        tmp_path = tmp_file.name
    try:
        img = Image.open(tmp_path)
        img_w = w_max
        img_h = (img.height / img.width) * img_w
        if img_h > h_max:
            img_h = h_max
            img_w = (img.width / img.height) * img_h
        
        # Calcular X para que el centro de la imagen coincida con x_center
        final_x = x_center - (img_w / 2)
        # Calcular Y para que la base de la imagen esté un poco sobre la línea
        final_y = y_bottom - img_h - 1
        
        pdf_obj.image(tmp_path, x=final_x, y=final_y, w=img_w, h=img_h)
    except Exception as e:
        st.error(f"Error al añadir imagen: {e}")

def create_checkbox_table(pdf, section_title, items, x_pos, item_w, col_w, row_h=3.4):
    pdf.set_x(x_pos)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 7.2)
    pdf.cell(item_w, row_h, f"  {section_title}", border=1, ln=0, align="L", fill=True)
    pdf.cell(col_w, row_h, "OK", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "NO", border=1, ln=0, align="C", fill=True)
    pdf.cell(col_w, row_h, "N/A", border=1, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", 6.2)
    for item, value in items:
        pdf.set_x(x_pos)
        pdf.cell(5, row_h, "", border=0)
        pdf.cell(item_w - 5, row_h, item, border=0)
        pdf.cell(col_w, row_h, "X" if value == "OK" else "", border=1, align="C")
        pdf.cell(col_w, row_h, "X" if value == "NO" else "", border=1, align="C")
        pdf.cell(col_w, row_h, "X" if value == "N/A" else "", border=1, align="C", ln=1)
    pdf.ln(1.5)

def draw_boxed_text_auto(pdf, x, y, w, min_h, title, text):
    pdf.set_xy(x, y)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 7.2)
    pdf.cell(w, 4.6, title, border=1, ln=1, fill=True)
    y_body = pdf.get_y()
    pdf.set_xy(x + 1.2, y_body + 1.2)
    pdf.set_font("Arial", "", 7.0)
    if text:
        pdf.multi_cell(w - 2.4, 3.2, text, border=0)
    final_y = max(y_body + min_h, pdf.get_y() + 1.2)
    pdf.rect(x, y_body, w, final_y - y_body)
    pdf.set_y(final_y)

# ========= app =========
def main():
    st.title("Pauta de Mantenimiento Preventivo - Incubadora")

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
            with col1: st.markdown(item)
            with col2: seleccion = st.radio("", ["OK", "NO", "N/A"], horizontal=True, key=item)
            respuestas.append((item, seleccion))
        return respuestas

    chequeo_visual = checklist("1. Chequeo visual", ["1.1. Ruedas", "1.2. Gabinetes", "1.3. Cable de poder", "1.4. Puerta"])
    grupo_motor = checklist("2. Grupo motor", ["2.1. Interruptor de poder", "2.2. Test de encendido", "2.3. Panel de control", "2.4. Control modo aire", "2.5. Calibración Temp (+/- 0.2)", "2.6. Motor/Aspa", "2.7. Alarma"])
    cuerpo = checklist("3. Cuerpo", ["3.1. Bacinete / bandejas", "3.2. Empaquetaduras", "3.3. Estanque humedad", "3.4. Microfiltro de aire", "3.5. Seguro de cúpula", "3.6. Mástil IV"])
    cupula = checklist("4. Cúpula", ["4.1. Sin trizaduras", "4.2. Puertas acceso", "4.3. Aros iris", "4.4. Pestillos"])
    seguridad_electrica = checklist("5. Seguridad eléctrica", ["5.1. Corriente fuga normal", "5.2. Corriente fuga neutro abierto"])

    st.subheader("6. Instrumentos de análisis")
    if "analisis_equipos" not in st.session_state: st.session_state.analisis_equipos = [{}, {}]
    for i, _ in enumerate(st.session_state.analisis_equipos):
        st.session_state.analisis_equipos[i]["equipo"] = st.text_input(f"Equipo {i+1}", key=f"e_{i}")
        st.session_state.analisis_equipos[i]["serie"] = st.text_input(f"Serie {i+1}", key=f"s_{i}")

    observaciones = st.text_area("Observaciones")
    operativo = st.radio("¿EQUIPO OPERATIVO?", ["SI", "NO"])
    tecnico = st.text_input("NOMBRE TÉCNICO/INGENIERO")
    empresa = st.text_input("EMPRESA RESPONSABLE")

    col1, col2, col3 = st.columns(3)
    with col1: st.write("Firma Técnico:"); canvas_tecnico = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, drawing_mode="freedraw", key="c_tec")
    with col2: st.write("Firma Ing. Clínica:"); canvas_ing = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, drawing_mode="freedraw", key="c_ing")
    with col3: st.write("Firma Personal Clínico:"); canvas_clin = st_canvas(stroke_width=3, stroke_color="#000", background_color="#EEE", height=150, width=250, drawing_mode="freedraw", key="c_cli")

    if st.button("Generar PDF"):
        pdf = PDF("L", "mm", "A4", footer_lines=FOOTER_LINES)
        pdf.set_margins(10, 10, 10)
        pdf.add_page()
        
        # --- Cabecera ---
        pdf.set_font("Arial", "B", 8)
        ideq_txt = f"IDEQ: {ideq}"
        ideq_w = pdf.get_string_width(ideq_txt) + 6
        pdf.set_xy(pdf.w - 10 - ideq_w, 5)
        pdf.cell(ideq_w, 6, ideq_txt, 1, 1, "C", fill=True)
        
        pdf.set_xy(10, 5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "PAUTA MANTENCIÓN PREVENTIVA INCUBADORA", 0, 1, "L")
        
        # --- Datos ---
        pdf.set_font("Arial", "", 8)
        col_w = (pdf.w - 20) / 2
        y_data = pdf.get_y()
        pdf.cell(col_w, 4, f"MARCA: {marca}", 0, 1)
        pdf.cell(col_w, 4, f"MODELO: {modelo}", 0, 1)
        pdf.cell(col_w, 4, f"NÚMERO DE SERIE: {sn}", 0, 1)
        pdf.cell(col_w, 4, f"UBICACIÓN: {ubicacion}", 0, 1)
        
        pdf.set_xy(10 + col_w, y_data)
        pdf.cell(col_w, 4, f"FECHA: {fecha}", 0, 1)
        pdf.cell(col_w, 4, f"N/INVENTARIO: {inventario}", 0, 1)

        # --- Checklists (Izquierda) ---
        pdf.set_y(y_data + 20)
        create_checkbox_table(pdf, "1. Chequeo Visual", chequeo_visual, 10, 60, 10)
        create_checkbox_table(pdf, "2. Grupo Motor", grupo_motor, 10, 60, 10)
        create_checkbox_table(pdf, "3. Cuerpo", cuerpo, 10, 60, 10)
        create_checkbox_table(pdf, "4. Cúpula", cupula, 10, 60, 10)
        create_checkbox_table(pdf, "5. Seguridad Eléctrica", seguridad_electrica, 10, 60, 10)

        # --- Columna Derecha ---
        y_right = y_data + 20
        pdf.set_xy(100, y_right)
        draw_boxed_text_auto(pdf, 100, y_right, 180, 15, "  6. Instrumentos de Análisis", 
                            "\n".join([f"- {d['equipo']} (S/N: {d['serie']})" for d in st.session_state.analisis_equipos if d.get('equipo')]))
        
        pdf.set_y(pdf.get_y() + 2)
        draw_boxed_text_auto(pdf, 100, pdf.get_y(), 180, 20, "  Observaciones", observaciones)
        
        pdf.set_y(pdf.get_y() + 5)
        pdf.set_x(100)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(40, 5, f"EQUIPO OPERATIVO: {operativo}", 0, 1)
        pdf.set_x(100)
        pdf.cell(0, 5, f"EMPRESA: {empresa}", 0, 1)
        
        # --- FIRMAS SECCIÓN ---
        y_firmas = pdf.h - 55
        line_w = 60
        
        # Posiciones de los centros de cada firma
        center_tec = 10 + (line_w / 2)
        center_ing = 100 + (line_w / 2)
        center_cli = 190 + (line_w / 2)

        # Dibujar Imágenes de Firmas (Centradas sobre la futura línea)
        add_signature_centered(pdf, canvas_tecnico, center_tec, y_firmas)
        add_signature_centered(pdf, canvas_ing, center_ing, y_firmas)
        add_signature_centered(pdf, canvas_clin, center_cli, y_firmas)

        # Dibujar Líneas
        pdf.set_draw_color(0)
        pdf.line(10, y_firmas, 10 + line_w, y_firmas)
        pdf.line(100, y_firmas, 100 + line_w, y_firmas)
        pdf.line(190, y_firmas, 190 + line_w, y_firmas)

        # Textos de Firmas
        pdf.set_font("Arial", "B", 7)
        # Técnico (Nombre arriba para que no lo tape la firma)
        pdf.set_xy(10, y_firmas + 1)
        pdf.multi_cell(line_w, 3.5, f"{tecnico}\nTÉCNICO RESPONSABLE", 0, "C")
        
        pdf.set_xy(100, y_firmas + 1)
        pdf.multi_cell(line_w, 3.5, "RECEPCIÓN CONFORME\nINGENIERÍA CLÍNICA", 0, "C")
        
        pdf.set_xy(190, y_firmas + 1)
        pdf.multi_cell(line_w, 3.5, "RECEPCIÓN CONFORME\nPERSONAL CLÍNICO", 0, "C")

        out = pdf.output(dest="S")
        st.download_button("Descargar PDF", bytes(out) if not isinstance(out, str) else out.encode("latin1"), 
                           file_name=f"MP_{ideq}_{sn}.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()
