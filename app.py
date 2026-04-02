import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Oficial", page_icon="🎯")

st.title("🎯 Gerador de Acesso Direto (Sem Propaganda)")
st.write("Versão otimizada para abertura imediata no Redmi/Xiaomi.")

# Entrada de link
url_input = st.text_input("Cole o link do seu jogo aqui:").strip()

if url_input:
    # 1. TRATAMENTO DE URL LIMPA
    # Forçamos o protocolo correto para o Android não se confundir
    url_final = url_input if url_input.startswith(("http://", "https://")) else f"https://{url_input}"

    try:
        # 2. O SEGREDO: QR CODE "Puro" com Micro=False
        # Usamos o nível de erro 'L' para que o QR Code tenha o MÍNIMO de pontos possível.
        # Quanto menos pontos, mais rápido o seu Redmi identifica como LINK.
        qr = segno.make_qr(url_final, error='l', boost_error=False)
        
        buf = BytesIO()
        # Escala 20 e borda larga (10) isolam o código de interferências da tela
        qr.save(buf, kind='png', scale=20, border=10)
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.success(f"Link Direto Configurado: {url_final}")
        st.image(byte_im, caption="Aponte a câmera e clique em 'Ir para o site'", width=450)

        st.download_button(
            label="📥 Baixar QR Code Limpo",
            data=byte_im,
            file_name="qrcode_jogo.png",
            mime="image/png"
        )

    except Exception as e:
        st.error("Verifique o link digitado.")

st.divider()
st.info("💡 **DICA:** Se o seu Redmi ainda mostrar 'Copiar Texto', afaste o celular da tela. Como o código agora é muito grande e nítido, a câmera precisa de espaço para reconhecer que é um comando de site.")
