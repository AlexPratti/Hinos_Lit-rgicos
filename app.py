import streamlit as st
import segno
import requests
from io import BytesIO

st.set_page_config(page_title="Gerador QR Oficial", page_icon="📲")

st.title("🎯 Gerador de QR Code (Acesso Direto)")
st.write("Esta versão utiliza encurtamento automático para garantir compatibilidade com Redmi/Xiaomi.")

# Entrada de link
url_input = st.text_input("Cole o link aqui (ex: seusite.streamlit.app):").strip()

if url_input:
    # 1. ENCURTAMENTO AUTOMÁTICO (O segredo para o Redmi)
    # Links .streamlit.app são longos e geram QR Codes que a Xiaomi confunde com texto.
    # Usamos a API do TinyURL para criar um link curto e 'amigável' para o Android.
    try:
        api_url = f"http://tinyurl.com{url_input}"
        response = requests.get(api_url)
        short_url = response.text
        
        st.success(f"Link otimizado para celulares: {short_url}")

        # 2. GERAÇÃO DO QR CODE (BAIXA DENSIDADE)
        # Com o link curto, o QR Code fica com poucos pontos, facilitando a leitura.
        qr = segno.make_qr(short_url, error='l')
        
        buf = BytesIO()
        # Scale 20 para quadrados gigantes e nítidos
        qr.save(buf, kind='png', scale=20, border=4)
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.image(byte_im, caption="APONTE A CÂMERA E CLIQUE NO BOTÃO 'IR PARA O SITE'", width=450)

        st.download_button(
            label="📥 Baixar QR Code para Impressão",
            data=byte_im,
            file_name="qrcode_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Erro ao processar o link: {e}")

st.divider()
st.warning("⚠️ **DICA PARA REDMI NOTE 11:** Ao ler o código, um banner amarelo ou ícone de globo aparecerá na tela da câmera. **Você deve tocar nele**. O sistema Xiaomi não abre sites sem o seu clique de confirmação.")
