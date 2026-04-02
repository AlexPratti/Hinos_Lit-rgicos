import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Final", page_icon="📲")

st.title("🎯 Gerador de QR Code (Link Direto)")
st.write("Esta versão foi otimizada para o sensor da Xiaomi ler o link sem erros.")

# Entrada de link
url_input = st.text_input("Cole o link aqui (ex: seusite.streamlit.app):").strip()

if url_input:
    try:
        # 1. LIMPEZA E FORMATAÇÃO
        if not url_input.startswith(("http://", "https://")):
            url_final = f"https://{url_input}"
        else:
            url_final = url_input

        # 2. O SEGREDO: Modo Alfanumérico e Erro Mínimo (L)
        # Reduzimos o QR Code ao estado mais simples possível.
        # Isso faz os "quadradinhos" ficarem enormes, facilitando o foco do Redmi.
        qr = segno.make_qr(url_final, error='l', boost_error=False)
        
        buf = BytesIO()
        # Scale 20 e Border 10 para criar contraste máximo e isolar o código de interferências
        qr.save(buf, kind='png', scale=20, border=10, dark='black', light='white')
        byte_im = buf.getvalue()

        # 3. EXIBIÇÃO
        st.success(f"Link validado: {url_final}")
        
        # Mostramos o QR Code com largura controlada para não estourar a tela
        st.image(byte_im, caption="APONTE A CÂMERA E CLIQUE NO ÍCONE DE GLOBO/SITE", width=450)

        st.download_button(
            label="📥 Baixar QR Code de Alta Compatibilidade",
            data=byte_im,
            file_name="qrcode_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error("Erro ao gerar o código. Verifique se o link está correto.")

st.divider()
st.warning("💡 **DICA FINAL PARA REDMI:** Ao ler o código, um ícone flutuante de 'globo' ou 'link' aparecerá. **Você deve tocar nele**. O sistema Xiaomi exige essa confirmação para abrir o navegador.")
