from pathlib import Path
import tempfile
import cv2
import streamlit as st
from contador_parafusos import Count_Parafuso


#esse é o codigo para a aplicação web, ele tem uma interface simples 
#e intuitiva, onde o usuário pode escolher entre enviar uma imagem da 
#galeria ou tirar uma foto usando a câmera do dispositivo.

st.set_page_config(
    page_title="Aferifuso",
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .main-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            font-size: 1.15rem;
            color: #555;
            margin-bottom: 1.5rem;
        }
        .hero-box {
            padding: 1.3rem 1.5rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #f6f7fb 0%, #ffffff 100%);
            border: 1px solid #e9e9ef;
            margin-bottom: 1.2rem;
        }
        .ok-box {
            padding: 1rem 1.2rem;
            border-radius: 14px;
            background: #ecfdf3;
            border: 1px solid #b7efc5;
            color: #0f5132;
            font-weight: 600;
        }
        .alert-box {
            padding: 1rem 1.2rem;
            border-radius: 14px;
            background: #fff4e5;
            border: 1px solid #ffcf8a;
            color: #7a4200;
            font-weight: 600;
        }
        .small-note {
            color: #666;
            font-size: 0.95rem;
        }
    </style>
    """,
    unsafe_allow_html=True,)

st.markdown('<div class="main-title">🔩 Aferifuso</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Sistema Inteligente de Contagem de Parafusos para Picking Industrial</div>',
    unsafe_allow_html=True,
)

st.info(
    """
    **Como usar:**

    1. Escolha se deseja enviar uma imagem da galeria ou tirar uma foto agora.
    2. Posicione os parafusos sobre um fundo limpo, com boa iluminação.
    3. O sistema informa a quantidade estimada, a confiança e emite alerta se houver risco de erro por agrupamento.
    """
)

#aqui eu optei por colocar as opções de entrada e configuração lado a lado para otimizar o 
#espaço e melhorar a experiência do usuário, especialmente em telas maiores e assim o usuário pode 
#escolher a forma de entrada da imagem e configurar a exibição das etapas do processamento sem precisar 
#rolar a página.
col_opcao, col_config = st.columns([2, 1])

with col_opcao:
    modo_entrada = st.radio(
        "Escolha a forma de entrada da imagem:",
        ["Selecionar imagem da galeria", "Tirar foto agora"],
        horizontal=True,
    )

with col_config:
    mostrar_etapas = st.toggle("Mostrar etapas do processamento", value=True)

arquivo = None

if modo_entrada == "Selecionar imagem da galeria":
    arquivo = st.file_uploader(
        "Envie uma foto dos parafusos",
        type=["jpg", "jpeg", "png"],
        help="Use uma imagem nítida, com os parafusos bem visíveis.",
    )
else:
    arquivo = st.camera_input(
        "Tire uma foto dos parafusos",
        help="No celular, essa opção abre a câmera do dispositivo.",
    )

#aqui eu escolhi exibir uma mensagem informativa e uma dica para o 
#usuário caso ele ainda não tenha selecionado ou tirado uma foto, 
#isso ajuda a orientar o usuário sobre o próximo passo e também a definir
#expectativas sobre a qualidade da imagem necessária para uma boa contagem. 
#Além disso, a dica sobre parafusos encostados é importante para alertar o usuário 
#sobre possíveis limitações do sistema e incentivar uma conferência visual, 
#oq pode melhorar a confiança no resultado final.'
if arquivo is None:
    st.info("Selecione uma imagem da galeria ou tire uma foto para iniciar a contagem.")
    st.markdown(
        """
        <p class="small-note">
        Dica: se os parafusos estiverem muito encostados, o sistema ainda dará uma estimativa,
        mas também mostrará um alerta solicitando conferência visual.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp:
    temp.write(arquivo.getvalue())
    caminho_temp = Path(temp.name)

contador = Count_Parafuso()
dados = contador.contar(caminho_temp, salvar_etapas=False, salvar_resultado=False)

st.divider()
st.subheader("Resultado da leitura")

col1, col2, col3 = st.columns(3)
col1.metric("Quantidade estimada", dados["quantidade"])
col2.metric("Confiança", f"{dados['confianca']}%")
col3.metric("Regiões detectadas", dados["objetos_detectados"])

if dados["alerta"]["revisar"]:
    st.markdown(
        f"""
        <div class="alert-box">
            ⚠️ Atenção: {dados['alerta']['mensagem']}<br><br>
            {dados['alerta']['recomendacao']}
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Por que esse alerta apareceu?"):
        for motivo in dados["alerta"]["motivos"]:
            st.write(f"- {motivo}")
else:
    st.markdown(
        """
        <div class="ok-box">
            ✅ Leitura confiável: não foram encontrados sinais fortes de sobreposição ou agrupamento crítico.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.subheader("Imagem analisada")
resultado_rgb = cv2.cvtColor(dados["resultado"], cv2.COLOR_BGR2RGB)
st.image(resultado_rgb, use_container_width=True)


#aqui eu quis colocar as etapas do processamento para os avaliadores entenderem melhor como o algoritmo chegou àquela contagem,
#isso torna a visualização mais organizada e fácil de comparar as diferentes etapas lado a lado.
if mostrar_etapas:
    st.subheader("Etapas do processamento")
    st.caption("Essas imagens ajudam a explicar o critério de tomada de decisão do algoritmo.")

    etapas = dados["etapas"]
    grade = [
        ("1. Original", "original"),
        ("2. Escala de cinza", "cinza"),
        ("3. Diferença do fundo", "diferenca_fundo"),
        ("4. Máscara final", "mascara_final"),
        ("5. Contornos detectados", "contornos"),
        ("6. Resultado final", "resultado"),
    ]

    for linha in range(0, len(grade), 3):
        cols = st.columns(3)
        for col, (titulo, chave) in zip(cols, grade[linha:linha + 3]):
            with col:
                st.write(f"**{titulo}**")
                imagem = etapas[chave]
                if len(imagem.shape) == 2:
                    st.image(imagem, use_container_width=True, clamp=True)
                else:
                    st.image(cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB), use_container_width=True)
