import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Final", page_icon="📲")

st.title("🎯 Gerador de QR Code: Link Direto")
st.write("Versão otimizada para sensores Redmi/Xiaomi (Sem Propaganda).")

# Entrada do link
url_input = st.text_input("Cole o link do seu jogo aqui:", placeholder="seujogo.streamlit.app").strip()

if url_input:
    # 1. LIMPEZA TOTAL DA URL
    # Remove protocolos extras e espaços para evitar que o Android ache que é texto
    url_limpa = url_input.replace("https://", "").replace("http://", "").replace(" ", "")
    url_final = f"https://{url_limpa}"

    try:
        # 2. O SEGREDO TÉCNICO: MODO BYTES + ERRO MÍNIMO
        # Usamos o modo de dados 'byte' e desativamos o 'boost_error'.
        # Isso gera o QR Code com a MENOR quantidade de pontos possível (Baixa Densidade).
        qr = segno.make_qr(url_final, error='l', boost_error=False)
        
        buf = BytesIO()
        # Escala 30 e Borda 10: O código fica gigante e com contraste máximo.
        # Isso impede que o sensor da Xiaomi confunda os pontos com 'caracteres de texto'.
        qr.save(buf, kind='png', scale=30, border=10)
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.success(f"Link configurado: {url_final}")
        
        # Mostramos o QR Code centralizado e bem grande
        st.image(byte_im, caption="APONTE A CÂMERA E CLIQUE NO ÍCONE DE GLOBO/LINK NO CANTO", width=500)

        st.download_button(
            label="📥 Baixar QR Code de Alta Fidelidade",
            data=byte_im,
            file_name="qrcode_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error("Erro ao gerar. Verifique o link.")

st.divider()
st.warning("⚠️ **Atenção no Redmi Note 11:** Ao apontar a câmera, o link NÃO abrirá sozinho. Um **banner amarelo ou um ícone de Globo** aparecerá no canto inferior. Você **PRECISA CLICAR NELE**. Se você clicar no centro da tela onde aparece o texto escrito, ele apenas copiará.")
