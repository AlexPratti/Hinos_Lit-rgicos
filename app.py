import streamlit as st
import pdfplumber
import re
from supabase import create_client
import pandas as pd

# Conexão
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def process_pdf(file):
    data = []
    current_n1 = "Sem Categoria"
    current_n2 = None
    current_text = []
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                texto = line.strip()
                if not texto or "Sumário" in texto: continue

                # Identifica Nível 1: CAIXA ALTA, sem números no início, sem muitos pontos
                is_n1 = texto.isupper() and not re.match(r'^\d+\.', texto) and "...." not in texto
                
                # Identifica Nível 2: Começa com número e ponto (ex: 1. VENHA A NÓS)
                is_n2 = re.match(r'^\d+\.', texto)

                if is_n1:
                    if current_n2:
                        data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
                    current_n1 = texto
                    current_n2 = None
                    current_text = []
                    # Força a existência da categoria N1
                    data.append({"n1": current_n1, "n2": None, "texto": ""})

                elif is_n2:
                    if current_n2:
                        data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
                    # Limpa restos de sumário (pontos e números de página no final)
                    current_n2 = re.sub(r'\s\.+\s\d+$', '', texto)
                    current_text = []
                
                else:
                    if current_n2 and not texto.isdigit():
                        current_text.append(texto)

    if current_n2:
        data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
    return data
def save_to_db(data):
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    categorias_unicas = sorted(list(set([item['n1'] for item in data if item['n1']])))
    for cat_nome in categorias_unicas:
        res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_nome}).execute()
        cat_id = res.data[0]['id']
        
        itens = [
            {"categoria_id": cat_id, "nome_nivel2": item['n2'], "texto_completo": item['texto']} 
            for item in data if item['n1'] == cat_nome and item['n2'] is not None
        ]
        if itens:
            supabase.table("hinos_conteudos").insert(itens).execute()

# --- INTERFACE ---
st.set_page_config(page_title="Hinário Litúrgico", layout="wide")

with st.expander("⬆️ Configurações de Upload (PDF)"):
    arquivo = st.file_uploader("Upload do arquivo PDF", type="pdf")
    if st.button("Atualizar Banco de Dados") and arquivo:
        dados = process_pdf(arquivo)
        save_to_db(dados)
        st.success(f"Processado: {len([d for d in dados if d['n2']])} hinos encontrados.")
        st.rerun()

# --- EXIBIÇÃO (Sua lógica original mantida) ---
try:
    res_cat = supabase.table("hinos_categorias").select("*").order("nome_nivel1").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        c1, c2 = st.columns(2)
        with c1:
            escolha_n1 = st.selectbox("Selecione a Categoria", df_cat['nome_nivel1'])
            id_n1 = int(df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].iloc[0])
        with c2:
            termo = st.text_input("🔍 Buscar hino por nome")

        query = supabase.table("hinos_conteudos").select("*").eq("categoria_id", id_n1)
        if termo: query = query.ilike("nome_nivel2", f"%{termo}%")
        hinos = query.execute().data

        if hinos:
            titulos_hinos = [h['nome_nivel2'] for h in hinos]
            hino_selecionado_nome = st.radio("Escolha o hino:", titulos_hinos)
            conteudo_hino = next(h for h in hinos if h['nome_nivel2'] == hino_selecionado_nome)
            st.markdown("---")
            st.subheader(conteudo_hino['nome_nivel2'])
            st.text(conteudo_hino['texto_completo']) # text mantém versos sem formatação code
        else:
            st.warning("Nenhum hino encontrado.")
except Exception as e:
    st.info("Aguardando upload do primeiro arquivo...")
