import streamlit as st
import segno
import pyshorteners
from io import BytesIO

# Configuração da Página
st.set_page_config(page_title="Gerador QR Forms Oficial", page_icon="📝")

st.title("🎯 Gerador de Acesso Direto para Formulários")
st.write("Este código encurta links longos (Google/Microsoft Forms) para garantir que o seu Redmi abra o site direto.")

# Entrada do link longo do formulário
form_url = st.text_input("Cole o link longo do seu formulário aqui:").strip()

if form_url:
    try:
        # 1. O PULO DO GATO: Encurtar o link
        # Links longos geram QR Codes densos que o Android lê como texto.
        # Encurtando, o QR Code fica simples e o celular identifica como LINK na hora.
        s = pyshorteners.Shortener()
        short_url = s.tinyurl.short(form_url)
        
        st.info(f"Link encurtado com sucesso: {short_url}")

        # 2. GERAÇÃO DO QR CODE COM SEGNO (PADRÃO ISO)
        # Usamos scale=20 para os quadrados ficarem gigantes e fáceis de focar
        qr = segno.make_qr(short_url)
        
        buf = BytesIO()
        qr.save(buf, kind='png', scale=20, border=4)
        byte_im = buf.getvalue()

        # 3. EXIBIÇÃO
        st.success("✅ QR Code pronto! Aponte a câmera para abrir o site.")
        st.image(byte_im, caption="DICA: No Redmi, clique no ícone de Globo que aparecerá.", width=400)

        # DOWNLOAD
        st.download_button(
            label="📥 Baixar QR Code para Impressão",
            data=byte_im,
            file_name="qrcode_forms_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Erro ao processar o link. Verifique se a URL está correta. Detalhe: {e}")

st.divider()
st.warning("⚠️ **POR QUE ISSO FUNCIONA?** Links de formulários são grandes demais para a câmera do Redmi Note 11 processar como link direto. Ao encurtar para um link 'TinyURL', o QR Code fica com poucos blocos, o que força o celular a reconhecer o comando de 'Abrir Navegador' instantaneamente.")
