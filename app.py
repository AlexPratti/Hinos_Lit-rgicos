import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd
import io

# Conexão original
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])
BUCKET = "hinarios"
FILE_PATH = "hinario_atual.pdf"

CATEGORIAS_ALVO = ["ORANTES", "INICIAIS E FINAIS", "PERDÃO", "GLÓRIA", "DEUS NOS FALA", "SALMO", "ACLAMAÇÃO", "OFERTÓRIO", "LOUVOR", "SANTO", "CORDEIRO", "PAZ", "COMUNHÃO", "BÍBLIA", "CRUZ", "LADAINHAS – SEQUÊNCIAS - PROCLAMAÇÕES", "MARIA", "PRECES"]

def process_pdf_with_crop_coords(file):
    data = []
    current_n1 = "Sem Categoria"
    with pdfplumber.open(file) as pdf:
        progresso = st.progress(0)
        for i, page in enumerate(pdf.pages):
            words = page.extract_words()
            lines = page.extract_text().split('\n')
            for line in lines:
                t_limpo = line.strip()
                if not t_limpo: continue
                if t_limpo.upper() in CATEGORIAS_ALVO:
                    current_n1 = t_limpo.upper()
                    continue
                if re.match(r'^\d+\.', t_limpo):
                    num_tit = t_limpo.split()[0]
                    y_top = next((float(w['top']) for w in words if w == num_tit), 0)
                    if data and data[-1]['pag_fim'] == i + 1:
                        data[-1]['y_fim'] = y_top - 5
                    data.append({
                        "n1": current_n1, "n2": t_limpo, "pag_inicio": i + 1,
                        "y_ini": y_top - 10 if y_top > 10 else 0,
                        "pag_fim": i + 1, "y_fim": float(page.height)
                    })
            progresso.progress((i + 1) / len(pdf.pages))
    return data

def get_persistent_pdf():
    try:
        res = supabase.storage.from_(BUCKET).download(FILE_PATH)
        return io.BytesIO(res)
    except: return None
def save_to_db(data):
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    for cat in CATEGORIAS_ALVO:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat}).execute()
        if res.data:
            cat_id = res.data[0]['id']
            itens = [{"categoria_id": cat_id, "nome_nivel2": item['n2'], 
                      "texto_completo": f"{item['pag_inicio']};{item['y_ini']};{item['y_fim']}"} 
                     for item in data if item['n1'] == cat]
            if itens: supabase.table("hinos_conteudos").insert(itens).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário Visual", layout="wide")
arquivo_persistente = get_persistent_pdf()

with st.expander("⬆️ Upload PDF"):
    novo = st.file_uploader("Selecione o arquivo", type="pdf")
    if st.button("Atualizar Banco") and novo:
        bytes_pdf = novo.read()
        supabase.storage.from_(BUCKET).upload(path=FILE_PATH, file=bytes_pdf, file_options={"x-upsert": "true"})
        dados = process_pdf_with_crop_coords(io.BytesIO(bytes_pdf))
        save_to_db(dados)
        st.success("Sincronizado! O erro deve sumir ao recarregar.")
        st.rerun()

try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data and arquivo_persistente:
        df_cat = pd.DataFrame(res_cat.data)
        c1, c2 = st.columns(2)
        with c1:
            escolha_n1 = st.selectbox("Categoria", df_cat['nome_nivel1'], key="cat")
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc[0])
        
        hinos = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1).execute().data
        if hinos:
            hinos_ord = sorted(hinos, key=lambda x: int(re.search(r'\d+', x['nome_nivel2']).group()))
            hino_sel = st.selectbox("Hino:", [h['nome_nivel2'] for h in hinos_ord], key=f"h_{escolha_n1}")
            item = next(h for h in hinos if h['nome_nivel2'] == hino_sel)
            
            # Tratamento para evitar erro de formato antigo
            if ";" in item['texto_completo']:
                c = item['texto_completo'].split(';')
                p_num, y_ini, y_fim = int(c[0]), float(c[1]), float(c[2])
                with pdfplumber.open(arquivo_persistente) as pdf:
                    page = pdf.pages[p_num - 1]
                    if y_fim <= y_ini: y_fim = float(page.height)
                    st.image(page.crop((0, y_ini, page.width, y_fim)).to_image(resolution=200).original, use_container_width=True)
            else:
                st.warning("Dados antigos detectados. Por favor, faça o upload do PDF novamente.")
    else: st.info("Aguardando upload do PDF...")
except Exception as e: st.error(f"Erro: {e}")
