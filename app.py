import streamlit as st
from docx import Document
from supabase import create_client
import pandas as pd
import re

# Conexão segura
supabase = create_client(st.secrets["URL_SUPABASE"], st.secrets["KEY_SUPABASE"])

def process_docx(file):
    doc = Document(file)
    data = []
    current_n1 = "GERAL"
    current_n2 = None
    current_text = []

    for para in doc.paragraphs:
        text = para.text.strip()
        
        # Ignora linhas vazias, sumário ou números de página isolados
        if not text or "...." in text or text.isdigit():
            continue

        # 1. Detectar Hinos (Nível 2) - Padrão: "1. ", "10. "
        if re.match(r'^\d+\.\s', text):
            if current_n2:
                data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
            current_n2 = text
            current_text = []
            continue

        # 2. Detectar Seções (Nível 1) - Todo em MAIÚSCULO e Curto
        # Ex: ORANTES, PERDÃO, INICIAIS E FINAIS
        if text.isupper() and len(text) < 50 and not text[0].isdigit():
            current_n1 = text
            continue

        # 3. Corpo do texto (Letras e Cifras)
        if current_n2:
            current_text.append(text)

    # Salva o último hino
    if current_n2:
        data.append({"n1": current_n1, "n2": current_n2, "texto": "\n".join(current_text)})
    
    return data

def save_to_db(data):
    # Limpa as tabelas (Ordem inversa por causa da Foreign Key)
    supabase.table("hinos_conteudos").delete().neq("id", 0).execute()
    supabase.table("hinos_categorias").delete().neq("id", 0).execute()
    
    seen_cats = {}
    for item in data:
        cat_name = item['n1']
        
        # Se a categoria ainda não foi inserida no banco neste processo
        if cat_name not in seen_cats:
            res = supabase.table("hinos_categorias").insert({"nome_nivel1": cat_name}).execute()
            # CORREÇÃO AQUI: res.data é uma LISTA, pegamos o primeiro item [0]
            if res.data:
                seen_cats[cat_name] = res.data[0]['id']
        
        # Insere o hino vinculado à categoria
        if cat_name in seen_cats:
            supabase.table("hinos_conteudos").insert({
                "categoria_id": seen_cats[cat_name],
                "nome_nivel2": item['n2'],
                "texto_completo": item['texto']
            }).execute()

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Hinário Litúrgico", layout="wide")

with st.sidebar:
    st.title("⚙️ Administração")
    arquivo = st.file_uploader("Selecione o arquivo .docx", type="docx")
    if st.button("🚀 Atualizar Banco de Dados"):
        if arquivo:
            with st.spinner("Processando documento..."):
                dados = process_docx(arquivo)
                if dados:
                    save_to_db(dados)
                    st.success(f"Sucesso! {len(dados)} hinos carregados.")
                    st.rerun()
                else:
                    st.error("Não foram encontrados hinos no padrão esperado.")

# --- VISUALIZAÇÃO ---
try:
    res_cat = supabase.table("hinos_categorias").select("*").order("id").execute()
    if res_cat.data:
        df_cat = pd.DataFrame(res_cat.data)
        
        col_menu, col_conteudo = st.columns([1, 2])
        
        with col_menu:
            st.subheader("Filtrar")
            escolha_n1 = st.selectbox("Seção:", df_cat['nome_nivel1'])
            cat_id = df_cat[df_cat['nome_nivel1'] == escolha_n1]['id'].values[0]
            
            busca = st.text_input("Buscar por nome:")
            
            # Busca hinos da categoria
            q = supabase.table("hinos_conteudos").select("*").eq("categoria_id", cat_id).order("id")
            if busca:
                q = q.ilike("nome_nivel2", f"%{busca}%")
            
            hinos_res = q.execute().data
            
            if hinos_res:
                lista_hinos = [h['nome_nivel2'] for h in hinos_res]
                hino_nome = st.radio("Selecione o hino:", lista_hinos)
                hino_selecionado = next(h for h in hinos_res if h['nome_nivel2'] == hino_nome)
            else:
                st.warning("Nenhum hino encontrado.")
                hino_selecionado = None

        with col_conteudo:
            if hino_selecionado:
                st.header(hino_selecionado['nome_nivel2'])
                st.divider()
                # Exibe o texto mantendo as quebras de linha
                st.text(hino_selecionado['texto_completo'])
    else:
        st.info("O banco de dados está vazio. Carregue um arquivo .docx no menu lateral.")

except Exception as e:
    st.error(f"Erro de conexão: {e}")
