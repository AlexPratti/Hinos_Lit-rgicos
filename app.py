import streamlit as st
import segno
from io import BytesIO

st.set_page_config(page_title="Gerador QR Oficial", page_icon="🎯")

st.title("🎯 Gerador de QR Code: Link Direto")
st.write("Esta versão foi otimizada para o seu Redmi Note 11 reconhecer o link do jogo.")

# Entrada de link
url_input = st.text_input("Cole o link do seu jogo aqui:", value="https://jogoforca-5thk4gttejzpjv5sugpyql.streamlit.app/").strip()

if url_input:
    # 1. TRATAMENTO DE URL
    # Garantimos o protocolo correto
    if not url_input.startswith(("http://", "https://")):
        url_final = f"https://{url_input}"
    else:
        url_final = url_input

    try:
        # 2. GERAÇÃO DE BAIXA DENSIDADE (MÁXIMO CONTRASTE)
        # Como o link é longo, forçamos o nível de erro 'L' (mínimo)
        # Isso faz o QR Code ter menos pontos, facilitando a leitura no Redmi
        qr = segno.make_qr(url_final, error='l', boost_error=False)
        
        buf = BytesIO()
        # Scale 25 e Border 10 criam o maior contraste possível para o sensor Xiaomi
        qr.save(buf, kind='png', scale=25, border=10, dark='black', light='white')
        byte_im = buf.getvalue()

        # EXIBIÇÃO
        st.success(f"Link configurado para o QR Code: {url_final}")
        
        # Mostramos o QR Code centralizado e bem nítido
        st.image(byte_im, caption="APONTE A CÂMERA E CLIQUE NO ÍCONE DE GLOBO/LINK NO CANTO", width=500)

        st.download_button(
            label="📥 Baixar QR Code de Alta Compatibilidade",
            data=byte_im,
            file_name="qrcode_jogo_direto.png",
            mime="image/png"
        )

    except Exception as e:
        st.error(f"Erro ao gerar: Verifique se o link está correto.")

st.divider()
st.info("💡 **DICA FINAL:** Se o seu Redmi ainda der 'Copiar Texto', afaste o celular da tela. O link longo gera muitos pontos; a câmera precisa de distância para focar em todos de uma vez e mostrar o botão 'Ir para o site'.")
