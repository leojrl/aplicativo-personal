import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
import base64
import hashlib
import hmac
import secrets
from datetime import date
from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

# ==========================================
# CONFIGURAÇÕES E DADOS BASE
# ==========================================
st.set_page_config(
    page_title="KN Alta Performance",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DIRETORIO_APP = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRETORIO_APP, "dados_treinos.json")
ARQUIVO_USUARIOS = os.path.join(DIRETORIO_APP, "usuarios.json")
CAMINHO_LOGO = os.path.join(DIRETORIO_APP, "1000370127.jpg")
USAR_FIRESTORE = os.getenv("FIRESTORE_ENABLED", "").lower() in {"1", "true", "yes"}
TAMANHO_MAXIMO_FOTO_PERFIL = 300 * 1024

MODALIDADES_ICONES = {
    "Futebol": "⚽ Futebol",
    "Futevôlei": "🏐 Futevôlei",
    "Beach Tênis": "🎾 Beach Tênis",
    "Tênis": "🎾 Tênis",
    "Basquete": "🏀 Basquete"
}

MODALIDADES_EXERCICIOS = {
    "Futebol": ["Passe curto", "Passe longo", "Finalização", "Controle de bola", "Drible", "Trabalho de pés", "Condicionamento físico"],
    "Futevôlei": ["Saque", "Recepção de peito", "Recepção de coxa", "Levantamento", "Ataque (Pingada)", "Ataque (Forte)", "Defesa"],
    "Beach Tênis": ["Saque", "Voleio de Forehand", "Voleio de Backhand", "Smash", "Lob", "Devolução", "Movimentação em areia"],
    "Tênis": ["Saque", "Forehand", "Backhand", "Smash", "Slice", "Footwork", "Drop Shot", "Topspin", "Devolução", "Rally de Fundo"],
    "Basquete": ["Arremesso (Jump)", "Lance Livre", "Bandeja", "Drible", "Passe de peito", "Passe picado", "Rebote"]
}

# Carrega logo em base64 se disponível
LOGO_BASE64 = None
if os.path.isfile(CAMINHO_LOGO):
    try:
        with open(CAMINHO_LOGO, "rb") as arquivo_logo:
            LOGO_BASE64 = base64.b64encode(arquivo_logo.read()).decode("ascii")
    except Exception:
        LOGO_BASE64 = None

@st.cache_data(show_spinner=False)
def carregar_fundo_logo_base64():
    if not os.path.isfile(CAMINHO_LOGO):
        return None
    try:
        imagem = Image.open(CAMINHO_LOGO).convert("RGB")
        imagem.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        imagem.save(buffer, format="JPEG", quality=75, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return None

FUNDO_LOGO_B64 = carregar_fundo_logo_base64()

# Injeta CSS de fundo com o logo do programa como marca d'água / wallpaper
if FUNDO_LOGO_B64:
    st.html(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-color: #070b13 !important;
            background-image: 
                radial-gradient(circle at 50% 50%, rgba(10, 15, 26, 0.65) 0%, rgba(7, 10, 18, 0.82) 65%, rgba(5, 7, 13, 0.94) 100%),
                url('data:image/jpeg;base64,{FUNDO_LOGO_B64}') !important;
            background-position: center center, center center !important;
            background-repeat: no-repeat, no-repeat !important;
            background-attachment: fixed, fixed !important;
            background-size: cover, min(750px, 85vmin) !important;
        }}
        section.main, [data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
            background: transparent !important;
        }}
        </style>
        """
    )

# ==========================================
# ESTILIZAÇÃO CSS GLOBAL (CAMPOS E MENUS COM LETRA PRETA)
# ==========================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@600;700;800;900&display=swap');

    :root {
        --kn-bg-dark: #0a0e17;
        --kn-card-bg: rgba(21, 29, 47, 0.88);
        --kn-border: rgba(255, 255, 255, 0.08);
        --kn-accent: #f5c400;
        --kn-cyan: #38bdf8;
        --kn-text-title: #ffffff;
        --kn-text-main: #e2e8f0;
        --kn-text-muted: #94a3b8;
    }

    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--kn-text-main);
    }

    h1, h2, h3, h4 {
        font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.02em;
        color: var(--kn-text-title) !important;
    }

    /* Fundo Studio / High-Performance Atmosphere de contingência */
    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 50% -10%, #18243c 0%, #0d1320 65%, #080c14 100%) fixed;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    [data-testid="stAppViewContainer"] main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1240px;
    }

    /* Barra Lateral */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b0f18 0%, #111827 50%, #0b0f19 100%) !important;
        border-right: 1px solid var(--kn-border) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.35);
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--kn-text-muted) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #e2e8f0 !important;
        font-weight: 700;
        font-size: 0.9rem;
    }

    /* ============================================================
       TODOS OS MENUS E CAMPOS DE DIGITAÇÃO: TEXTO EM COR PRETO
       ============================================================ */
    input, textarea {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
    }

    div[data-baseweb="input"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] {
        background-color: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="textarea"]:focus-within {
        border-color: #f5c400 !important;
        box-shadow: 0 0 0 3px rgba(245, 196, 0, 0.3) !important;
    }

    /* Textos selecionados dentro do Selectbox em PRETO */
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
        color: #000000 !important;
        font-weight: 600;
    }

    /* Menus suspensos / Dropdowns com fundo branco e letras PRETAS */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"],
    li[role="option"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    li[role="option"] span,
    li[role="option"] div,
    li[role="option"] p {
        color: #000000 !important;
        font-weight: 600 !important;
    }

    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #fef08a !important;
        color: #000000 !important;
    }

    ::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        font-weight: 400 !important;
    }

    /* Cards e Containers */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--kn-card-bg) !important;
        border: 1px solid var(--kn-border) !important;
        border-radius: 18px !important;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.32) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
    }

    /* Métricas / KPI Cards */
    [data-testid="stMetric"] {
        background: var(--kn-card-bg) !important;
        border: 1px solid var(--kn-border) !important;
        border-radius: 16px !important;
        padding: 1.15rem 1.3rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.28) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        position: relative;
        overflow: hidden;
    }

    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--kn-accent) 0%, var(--kn-cyan) 100%);
    }

    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--kn-text-muted) !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-weight: 600 !important;
    }

    /* Abas de Navegação */
    [data-testid="stTabs"] [role="tablist"] {
        gap: 0.6rem !important;
        border-bottom: 1px solid var(--kn-border) !important;
        padding-bottom: 0.4rem !important;
        margin-bottom: 1.5rem !important;
    }

    [data-testid="stTabs"] button[role="tab"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid transparent !important;
        border-radius: 12px !important;
        padding: 0.55rem 1.3rem !important;
        color: var(--kn-text-muted) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stTabs"] button[role="tab"]:hover {
        background: rgba(255, 255, 255, 0.07) !important;
        color: #ffffff !important;
    }

    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: var(--kn-card-bg) !important;
        border: 1px solid rgba(245, 196, 0, 0.4) !important;
        color: var(--kn-accent) !important;
        box-shadow: 0 4px 16px rgba(245, 196, 0, 0.18) !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background: var(--kn-card-bg) !important;
        border: 1px solid var(--kn-border) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.22) !important;
        margin-bottom: 0.9rem !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] details summary {
        padding: 0.95rem 1.25rem !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        color: #ffffff !important;
        background: var(--kn-card-bg) !important;
    }

    [data-testid="stExpander"] details summary svg {
        color: var(--kn-accent) !important;
    }

    /* Botões */
    div[data-testid="stButton"] > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.4rem !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #f5c400 0%, #eab308 100%) !important;
        border: none !important;
        color: #0b0f19 !important;
        box-shadow: 0 4px 18px rgba(245, 196, 0, 0.28) !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(245, 196, 0, 0.42) !important;
    }

    div[data-testid="stButton"] > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid var(--kn-border) !important;
        color: #e2e8f0 !important;
    }

    /* Estilização da Foto Circular do Atleta via st.image */
    .kn-photo-frame img {
        border-radius: 50% !important;
        border: 4px solid #f5c400 !important;
        box-shadow: 0 8px 28px rgba(245, 196, 0, 0.4) !important;
        margin: 0 auto !important;
        display: block !important;
        object-fit: cover !important;
        aspect-ratio: 1 / 1 !important;
    }

    .kn-athlete-placeholder {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: #162032;
        border: 3.5px dashed rgba(245, 196, 0, 0.55);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 4rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        margin: 0 auto 0.8rem;
    }

    .kn-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        background: rgba(245, 196, 0, 0.12);
        color: #f5c400;
        border: 1px solid rgba(245, 196, 0, 0.28);
    }

    .kn-chip-cyan {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.28);
    }

    .kn-data-grid {
        display: flex;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 1.1rem;
        width: 100%;
    }

    .kn-data-card {
        flex: 1 1 120px;
        min-width: 110px;
        max-width: 150px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 14px;
        padding: 10px 12px;
        text-align: center;
    }

    .kn-data-label {
        font-size: 0.72rem;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-bottom: 3px;
    }

    .kn-data-value {
        font-size: 1.25rem;
        font-weight: 800;
        color: #ffffff;
        font-family: 'Outfit', sans-serif;
    }

    .kn-stat-badge {
        display: flex;
        flex-direction: column;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 8px 14px;
        min-width: 100px;
    }

    .kn-coach-note {
        background: rgba(245, 196, 0, 0.06);
        border-left: 3px solid #f5c400;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-top: 10px;
        color: #e2e8f0;
        font-size: 0.92rem;
        line-height: 1.45;
    }

    .kn-sidebar-user {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 12px 14px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .kn-success-card {
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 16px;
        padding: 1.5rem;
        display: flex;
        align-items: center;
        gap: 16px;
        margin-top: 12px;
    }

    .kn-empty-video {
        background: rgba(255, 255, 255, 0.02);
        border: 1px dashed rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 2.2rem 1.5rem;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# FUNÇÕES DE BANCO DE DADOS (JSON / FIRESTORE)
# ==========================================
@st.cache_resource(show_spinner=False)
def cliente_firestore():
    from google.cloud import firestore
    return firestore.Client()

def carregar_dados(usuario):
    if USAR_FIRESTORE:
        alunos = {}
        colecao = cliente_firestore().collection("contas").document(usuario).collection("alunos")
        for documento in colecao.stream():
            registro = documento.to_dict()
            nome = registro.pop("nome", documento.id)
            alunos[nome] = registro
        return alunos

    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    else:
        dados = {"versao": 2, "contas": {}}

    if dados.get("versao") == 2 and isinstance(dados.get("contas"), dict):
        return dados["contas"].get(usuario, {})

    usuarios = carregar_usuarios()
    contas = {}
    if usuarios:
        primeiro_usuario = next(iter(usuarios))
        contas[primeiro_usuario] = dados
    salvar_arquivo_dados({"versao": 2, "contas": contas})
    return contas.get(usuario, {})

def salvar_arquivo_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def salvar_usuarios(usuarios):
    if USAR_FIRESTORE:
        colecao = cliente_firestore().collection("usuarios")
        for nome, registro in usuarios.items():
            colecao.document(nome).set(registro)
        return

    with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as arquivo:
        json.dump(usuarios, arquivo, indent=4, ensure_ascii=False)

def salvar_dados(dados_usuario, usuario):
    usuarios = carregar_usuarios()
    if usuarios.get(usuario, {}).get("tipo") != "admin":
        raise PermissionError("Somente o administrador pode alterar os treinos.")

    if USAR_FIRESTORE:
        colecao = cliente_firestore().collection("contas").document(usuario).collection("alunos")
        documentos_existentes = {
            documento.id: documento
            for documento in colecao.stream()
        }
        nomes_salvos = set()
        for nome, dados_aluno in dados_usuario.items():
            identificador = hashlib.sha256(nome.encode("utf-8")).hexdigest()
            colecao.document(identificador).set({"nome": nome, **dados_aluno})
            nomes_salvos.add(identificador)
        for identificador, documento in documentos_existentes.items():
            if identificador not in nomes_salvos:
                documento.reference.delete()
        return

    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    else:
        dados = {"versao": 2, "contas": {}}

    if dados.get("versao") != 2 or not isinstance(dados.get("contas"), dict):
        usuarios = carregar_usuarios()
        contas = {}
        if usuarios:
            contas[next(iter(usuarios))] = dados
        dados = {"versao": 2, "contas": contas}

    dados["contas"][usuario] = dados_usuario
    salvar_arquivo_dados(dados)

def carregar_usuarios():
    if USAR_FIRESTORE:
        usuarios = {
            documento.id: documento.to_dict()
            for documento in cliente_firestore().collection("usuarios").stream()
        }
        return usuarios

    if os.path.exists(ARQUIVO_USUARIOS):
        with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as arquivo:
            usuarios = json.load(arquivo)
    else:
        return {}

    alterado = False
    if usuarios and not any(
        registro.get("tipo") == "admin" for registro in usuarios.values()
    ):
        primeiro_usuario = next(iter(usuarios))
        usuarios[primeiro_usuario]["tipo"] = "admin"
        alterado = True

    if alterado:
        salvar_usuarios(usuarios)
    return usuarios

def gerar_hash_senha(senha, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt.encode("ascii"), 310_000
    ).hex()

# ==========================================
# GESTÃO DE SESSÃO PERSISTENTE (ANTI-DESCONEXÃO NO F5)
# ==========================================
SEGREDO_SESSAO = "kn_alta_performance_session_secret_key_v1"

def gerar_token_sessao(usuario, registro):
    dados = f"{usuario}:{registro.get('hash', '')}"
    assinatura = hmac.new(
        SEGREDO_SESSAO.encode("utf-8"),
        dados.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    payload = f"{usuario}:{assinatura}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")

def validar_token_sessao(token, usuarios_dict):
    if not token or not isinstance(token, str):
        return None
    try:
        conteudo = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        if ":" not in conteudo:
            return None
        usuario, assinatura = conteudo.split(":", 1)
        registro = usuarios_dict.get(usuario)
        if not registro:
            return None
        dados = f"{usuario}:{registro.get('hash', '')}"
        esperada = hmac.new(
            SEGREDO_SESSAO.encode("utf-8"),
            dados.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(esperada, assinatura):
            return usuario
    except Exception:
        return None
    return None

def preparar_foto_perfil(arquivo):
    imagem = Image.open(BytesIO(arquivo.getvalue()))
    imagem = ImageOps.exif_transpose(imagem)

    for dimensao in (512, 384, 256):
        imagem.thumbnail((dimensao, dimensao))
        miniatura = imagem.convert("RGB")
        for qualidade in (85, 75, 65, 55, 45, 35):
            buffer = BytesIO()
            miniatura.save(buffer, format="JPEG", optimize=True, quality=qualidade)
            if buffer.tell() <= TAMANHO_MAXIMO_FOTO_PERFIL:
                base64_str = base64.b64encode(buffer.getvalue()).decode("ascii")
                return f"data:image/jpeg;base64,{base64_str}"

    raise ValueError("A foto é muito grande. Escolha uma imagem menor.")

def calcular_imc(peso_kg, altura_cm):
    if peso_kg is None or altura_cm is None or altura_cm <= 0:
        return None
    altura_m = altura_cm / 100
    return peso_kg / (altura_m * altura_m)

def obter_perfil_atleta(nome_aluno, usuarios_dict):
    perfil = {}
    if nome_aluno in st.session_state.db and isinstance(st.session_state.db[nome_aluno], dict):
        perfil = dict(st.session_state.db[nome_aluno].get("perfil", {}))

    for u_nome, u_reg in usuarios_dict.items():
        if u_reg.get("aluno") == nome_aluno or u_nome.casefold() == nome_aluno.casefold():
            u_perf = u_reg.get("perfil", {})
            for k, v in u_perf.items():
                if v is not None and not perfil.get(k):
                    perfil[k] = v
            break
    return perfil

# ==========================================
# GRÁFICOS PERSONALIZADOS (MATPLOTLIB PRO)
# ==========================================
def plot_distribuicao_exercicios(df_treinos):
    contagem = df_treinos['exercicio'].value_counts()
    cores = ['#F5C400', '#38BDF8', '#818CF8', '#34D399', '#FB923C', '#F472B6', '#E879F9']
    
    fig, ax = plt.subplots(figsize=(6, 4.4), facecolor='none')
    ax.set_facecolor('none')
    
    wedges, texts, autotexts = ax.pie(
        contagem,
        labels=contagem.index,
        autopct='%1.0f%%',
        pctdistance=0.76,
        startangle=120,
        colors=cores[:len(contagem)],
        wedgeprops=dict(width=0.42, edgecolor='#0f1523', linewidth=2.5),
        textprops=dict(color='#cbd5e1', fontsize=9.5, fontweight='500')
    )
    for autotext in autotexts:
        autotext.set_color('#ffffff')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
        
    ax.axis('equal')
    plt.tight_layout()
    return fig

def plot_volume_series(df_treinos):
    volume = df_treinos.groupby('exercicio')['series'].sum().sort_values()
    
    fig, ax = plt.subplots(figsize=(6, 4.4), facecolor='none')
    ax.set_facecolor('none')
    
    y_pos = range(len(volume))
    bars = ax.barh(y_pos, volume.values, color='#F5C400', height=0.52, edgecolor='none', zorder=3)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(volume.index, color='#f1f5f9', fontsize=9.5, fontweight='600')
    ax.set_xlabel("Número de Séries", color='#94a3b8', fontsize=9.5, labelpad=8)
    
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    ax.tick_params(colors='#94a3b8', labelsize=9)
    ax.grid(axis='x', color='#ffffff', alpha=0.08, linestyle='--', zorder=0)
    
    ax.bar_label(bars, padding=6, color='#ffffff', fontweight='bold', fontsize=9.5)
    
    if len(volume) > 0:
        max_val = max(volume.values)
        ax.set_xlim(0, max_val * 1.25)
        
    plt.tight_layout()
    return fig

# ==========================================
# TELA DE LOGIN (TODAS AS LETRAS EM PRETO)
# ==========================================
def mostrar_tela_login():
    st.markdown(
        """
        <style>
        /* Card de login branco com borda e sombra */
        .st-key-card_login_box {
            background-color: rgba(255, 255, 255, 0.95) !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 24px !important;
            padding: 1.5rem !important;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.55) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
        }

        /* OBRIGA LETRA PRETA EM TODOS OS ELEMENTOS DO MENU INICIAL */
        .st-key-card_login_box h1,
        .st-key-card_login_box h2,
        .st-key-card_login_box h3,
        .st-key-card_login_box p,
        .st-key-card_login_box span,
        .st-key-card_login_box label,
        [data-testid="stAppViewContainer"] main [data-testid="stForm"] label,
        [data-testid="stAppViewContainer"] main [data-testid="stForm"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stWidgetLabel"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stWidgetLabel"] label,
        [data-testid="stAppViewContainer"] main [data-testid="stCaptionContainer"] p,
        [data-testid="stAppViewContainer"] main [data-testid="stTabs"] button[role="tab"] {
            color: #000000 !important;
            font-weight: 700 !important;
        }

        /* TEXTO DIGITADO PELO USUÁRIO TOTALMENTE PRETO */
        [data-testid="stAppViewContainer"] main input,
        [data-testid="stAppViewContainer"] main div[data-baseweb="input"] input {
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            background-color: #f8fafc !important;
        }

        [data-testid="stAppViewContainer"] main div[data-baseweb="input"] {
            background-color: #f8fafc !important;
            border: 2px solid #94a3b8 !important;
            border-radius: 12px !important;
        }

        [data-testid="stAppViewContainer"] main div[data-baseweb="input"]:focus-within {
            border-color: #f5c400 !important;
            box-shadow: 0 0 0 3px rgba(245, 196, 0, 0.35) !important;
        }

        ::placeholder {
            color: #64748b !important;
            -webkit-text-fill-color: #64748b !important;
            font-weight: 500 !important;
        }

        /* Abas no Login com letras PRETAS */
        [data-testid="stTabs"] button[role="tab"] {
            color: #000000 !important;
            font-weight: 800 !important;
            background: #e2e8f0 !important;
            border-radius: 10px !important;
            padding: 0.55rem 1.25rem !important;
            border: 1px solid #cbd5e1 !important;
        }

        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: #f5c400 !important;
            color: #000000 !important;
            border: 1px solid #eab308 !important;
            box-shadow: 0 4px 12px rgba(245, 196, 0, 0.35) !important;
        }

        /* Botão com texto em PRETO */
        div[data-testid="stForm"] button[kind="primary"] {
            background: linear-gradient(135deg, #f5c400 0%, #eab308 100%) !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 16px rgba(245, 196, 0, 0.35) !important;
        }

        div[data-testid="stForm"] button[kind="primary"] p {
            color: #000000 !important;
            font-weight: 800 !important;
            font-size: 1.05rem !important;
        }

        /* Foto / Logo centralizada no menu de login */
        .st-key-card_login_box [data-testid="stImage"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 auto 0.6rem auto !important;
            text-align: center !important;
        }

        .st-key-card_login_box [data-testid="stImage"] img {
            border-radius: 20px !important;
            border: 3px solid #f5c400 !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.22) !important;
            margin: 0 auto !important;
            display: block !important;
            object-fit: cover !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, centro, _ = st.columns([1, 1.8, 1])
    with centro:
        st.write("")
        with st.container(border=True, key="card_login_box"):
            if os.path.isfile(CAMINHO_LOGO):
                st.image(CAMINHO_LOGO, width=140)

            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 1.2rem; margin-top: 0.4rem;">
                    <span style="display: inline-block; background: #f5c400; color: #000000; border-radius: 20px; padding: 5px 16px; font-size: 0.82rem; font-weight: 800; letter-spacing: 0.05em; margin-bottom: 0.6rem;">
                        ⚡ KN ALTA PERFORMANCE
                    </span>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; color: #000000;">Acesse sua conta</h2>
                    <p style="color: #1f2937; font-size: 0.95rem; margin: 0; font-weight: 600;">
                        Plataforma de Gestão e Treinamento Esportivo Personalizado
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            aba_entrar, aba_cadastro = st.tabs(["🔑 Entrar no Sistema", "📝 Criar Usuário"])
            usuarios = carregar_usuarios()

            with aba_entrar:
                with st.form("form_login"):
                    usuario = st.text_input("Usuário", key="login_usuario", placeholder="Digite seu usuário").strip().lower()
                    senha = st.text_input("Senha", type="password", key="login_senha", placeholder="••••••••")
                    entrar = st.form_submit_button("Entrar no Painel", type="primary", use_container_width=True)
                if entrar:
                    registro = usuarios.get(usuario)
                    if registro and hmac.compare_digest(
                        gerar_hash_senha(senha, registro["salt"]), registro["hash"]
                    ):
                        st.session_state.usuario_autenticado = usuario
                        st.query_params["session"] = gerar_token_sessao(usuario, registro)
                        st.rerun()
                    st.error("Usuário ou senha incorretos.")

            with aba_cadastro:
                if any(registro.get("tipo") == "admin" for registro in usuarios.values()):
                    st.caption("A nova conta será de atleta/usuário. O treinador associará o treino em seguida.")
                else:
                    st.caption("⚡ A primeira conta cadastrada será o administrador/treinador.")
                with st.form("form_cadastro"):
                    novo_usuario = st.text_input("Nome de usuário", key="cadastro_usuario", placeholder="Ex: joaosilva").strip().lower()
                    nova_senha = st.text_input("Senha (mínimo de 8 caracteres)", type="password", key="cadastro_senha", placeholder="Mínimo 8 caracteres")
                    confirmar_senha = st.text_input("Confirme a senha", type="password", key="confirmar_senha", placeholder="Repita a senha")
                    cadastrar = st.form_submit_button("Criar Minha Conta", type="primary", use_container_width=True)
                if cadastrar:
                    if len(novo_usuario) < 3 or len(novo_usuario) > 32:
                        st.error("O usuário deve ter entre 3 e 32 caracteres.")
                    elif not all(caractere.isalnum() or caractere in "._-" for caractere in novo_usuario):
                        st.error("Use apenas letras, números, ponto, hífen ou sublinhado no usuário.")
                    elif novo_usuario in usuarios:
                        st.error("Esse usuário já existe.")
                    elif len(nova_senha) < 8:
                        st.error("A senha deve ter pelo menos 8 caracteres.")
                    elif nova_senha != confirmar_senha:
                        st.error("As senhas não coincidem.")
                    else:
                        salt = secrets.token_hex(16)
                        novo_reg = {
                            "salt": salt,
                            "hash": gerar_hash_senha(nova_senha, salt),
                            "tipo": "admin" if not any(
                                registro.get("tipo") == "admin"
                                for registro in usuarios.values()
                            ) else "usuario",
                        }
                        usuarios[novo_usuario] = novo_reg
                        salvar_usuarios(usuarios)
                        st.session_state.usuario_autenticado = novo_usuario
                        st.query_params["session"] = gerar_token_sessao(novo_usuario, novo_reg)
                        st.rerun()

# ==========================================
# CONTROLE DE SESSÃO E ACESSO
# ==========================================
usuarios = carregar_usuarios()

# Se não estiver no session_state, tenta restaurar sessão salva na URL (evita desconectar no reload F5)
if not st.session_state.get("usuario_autenticado"):
    token_sessao = st.query_params.get("session") or st.query_params.get("auth")
    if token_sessao:
        usuario_recuperado = validar_token_sessao(token_sessao, usuarios)
        if usuario_recuperado:
            st.session_state.usuario_autenticado = usuario_recuperado
        else:
            st.query_params.clear()

if not st.session_state.get("usuario_autenticado"):
    mostrar_tela_login()
    st.stop()

usuario_autenticado = st.session_state.usuario_autenticado
registro_usuario = usuarios.get(usuario_autenticado)
if not registro_usuario:
    st.query_params.clear()
    st.session_state.pop("usuario_autenticado", None)
    st.stop()

# Garante que o token de sessão esteja gravado na URL do navegador para futuros recarregamentos
token_atual = st.query_params.get("session")
if not token_atual or validar_token_sessao(token_atual, usuarios) != usuario_autenticado:
    st.query_params["session"] = gerar_token_sessao(usuario_autenticado, registro_usuario)

eh_admin = registro_usuario.get("tipo") == "admin"
contas_admin = [
    nome for nome, registro in usuarios.items()
    if registro.get("tipo") == "admin"
]
conta_admin = next(iter(contas_admin), None)
if not eh_admin and not conta_admin:
    st.error("Nenhuma conta administradora está configurada.")
    st.stop()

if eh_admin:
    conta_dados = usuario_autenticado
    dados_conta = carregar_dados(conta_dados)
    aluno_atribuido = None
else:
    conta_admin_usuario = registro_usuario.get("conta_admin")
    aluno_atribuido = registro_usuario.get("aluno")
    conta_dados = conta_admin_usuario if conta_admin_usuario in contas_admin else None
    dados_conta = carregar_dados(conta_dados) if conta_dados else {}

    if not aluno_atribuido or aluno_atribuido not in dados_conta:
        contas_com_dados = {
            admin: dados_conta if admin == conta_dados else carregar_dados(admin)
            for admin in contas_admin
        }
        candidatos = [
            (admin, nome)
            for admin, alunos in contas_com_dados.items()
            for nome in alunos
            if aluno_atribuido and nome == aluno_atribuido
        ]
        if not candidatos:
            candidatos = [
                (admin, nome)
                for admin, alunos in contas_com_dados.items()
                for nome in alunos
                if nome.casefold() == usuario_autenticado.casefold()
            ]
            alunos_com_treino = [
                candidato for candidato in candidatos
                if contas_com_dados[candidato[0]][candidato[1]].get("treinos")
            ]
            if len(alunos_com_treino) == 1:
                candidatos = alunos_com_treino
            correspondencias_exatas = [
                candidato for candidato in candidatos
                if candidato[1] == usuario_autenticado
            ]
            if correspondencias_exatas:
                candidatos = correspondencias_exatas

        if len(candidatos) == 1:
            conta_dados, aluno_atribuido = candidatos[0]
            dados_conta = contas_com_dados[conta_dados]
            registro_usuario["conta_admin"] = conta_dados
            registro_usuario["aluno"] = aluno_atribuido
            salvar_usuarios(usuarios)
        else:
            if not conta_dados:
                conta_dados = conta_admin
                dados_conta = contas_com_dados[conta_dados]
            aluno_atribuido = None

chave_sessao_dados = (conta_dados, usuario_autenticado, aluno_atribuido)
if st.session_state.get("usuario_dados") != chave_sessao_dados:
    if eh_admin:
        st.session_state.db = dados_conta
    elif aluno_atribuido in dados_conta:
        st.session_state.db = {aluno_atribuido: dados_conta[aluno_atribuido]}
    else:
        st.session_state.db = {}
    st.session_state.usuario_dados = chave_sessao_dados

def atualizar_db():
    if not eh_admin:
        raise PermissionError("Somente o administrador pode alterar os treinos.")
    salvar_dados(st.session_state.db, conta_dados)

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    if os.path.exists(CAMINHO_LOGO):
        st.image(CAMINHO_LOGO, width=220)
    else:
        st.markdown("### ⚡ KN ALTA PERFORMANCE")

    st.markdown(
        f"""
        <div class="kn-sidebar-user">
            <span style="font-size: 1.5rem;">{'👑' if eh_admin else '⚡'}</span>
            <div style="flex: 1; overflow: hidden;">
                <div style="font-weight: 700; color: #ffffff; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
                    {usuario_autenticado}
                </div>
                <div style="font-size: 0.75rem; color: {'#f5c400' if eh_admin else '#38bdf8'}; font-weight: 700; text-transform: uppercase;">
                    {'Administrador' if eh_admin else 'Atleta'}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sair = st.button("↩  Sair da conta", key="btn_logout", use_container_width=True)
    if sair:
        st.query_params.clear()
        st.session_state.pop("usuario_autenticado", None)
        st.session_state.pop("db", None)
        st.session_state.pop("usuario_dados", None)
        st.rerun()

    st.divider()

    alunos_existentes = list(st.session_state.db.keys())
    aluno_atual = None

    if eh_admin:
        st.markdown("#### ⚡ Gestão de Alunos")
        opcao_aluno = st.selectbox(
            "Selecione o Aluno",
            ["+ Novo Aluno"] + alunos_existentes,
            key="sb_selecionar_aluno"
        )

        if opcao_aluno == "+ Novo Aluno":
            with st.container():
                st.markdown("**Cadastrar Novo Aluno**")
                novo_nome = st.text_input("Nome Completo", placeholder="Ex.: Lucas Lima")
                nova_modalidade = st.selectbox(
                    "Modalidade Principal",
                    list(MODALIDADES_EXERCICIOS.keys()),
                    format_func=lambda m: MODALIDADES_ICONES.get(m, m)
                )

                if st.button("Cadastrar Aluno", type="primary", use_container_width=True):
                    if novo_nome and novo_nome not in st.session_state.db:
                        st.session_state.db[novo_nome] = {
                            "modalidade": nova_modalidade,
                            "treinos": []
                        }
                        atualizar_db()
                        st.success(f"Aluno {novo_nome} cadastrado com sucesso!")
                        st.rerun()
                    elif novo_nome in st.session_state.db:
                        st.error("Aluno já cadastrado!")
                    else:
                        st.error("Informe o nome do aluno.")
        else:
            aluno_atual = opcao_aluno

        st.divider()
        st.markdown("#### 🔗 Vincular Usuário ao Treino")
        contas_usuarios = [
            nome for nome, registro in usuarios.items()
            if registro.get("tipo") != "admin"
        ]
        if not contas_usuarios:
            st.info("Crie uma conta de usuário pela tela inicial para vincular.")
        elif not alunos_existentes:
            st.info("Cadastre um aluno antes de vincular.")
        else:
            usuario_vinculo = st.selectbox("Conta de Login", contas_usuarios, key="sb_user_vinc")
            opcoes_vinculo = ["Sem vínculo"] + alunos_existentes
            vinculo_atual = usuarios[usuario_vinculo].get("aluno")
            indice_vinculo = (
                opcoes_vinculo.index(vinculo_atual)
                if vinculo_atual in opcoes_vinculo
                and usuarios[usuario_vinculo].get("conta_admin", conta_dados) == conta_dados
                else 0
            )
            aluno_vinculo = st.selectbox(
                "Aluno Liberado",
                opcoes_vinculo,
                index=indice_vinculo,
                key="sb_aluno_vinc",
                format_func=lambda n: n if n == "Sem vínculo" else f"{n} ({len(st.session_state.db[n].get('treinos', []))} ex.)"
            )
            if st.button("Salvar Vínculo", use_container_width=True):
                if aluno_vinculo == "Sem vínculo":
                    usuarios[usuario_vinculo].pop("aluno", None)
                    usuarios[usuario_vinculo].pop("conta_admin", None)
                else:
                    usuarios[usuario_vinculo]["aluno"] = aluno_vinculo
                    usuarios[usuario_vinculo]["conta_admin"] = conta_dados
                salvar_usuarios(usuarios)
                st.success("Vínculo salvo com sucesso!")
                st.rerun()

        if aluno_atual:
            st.divider()
            st.markdown(f"#### ➕ Adicionar Exercício")
            modalidade_aluno = st.session_state.db[aluno_atual]["modalidade"]
            st.caption(f"Modalidade: **{MODALIDADES_ICONES.get(modalidade_aluno, modalidade_aluno)}**")

            lista_exercicios = MODALIDADES_EXERCICIOS.get(modalidade_aluno, [])
            opcao_personalizada = "+ Outro exercício"
            exercicio_selecionado = st.selectbox(
                "Exercício", lista_exercicios + [opcao_personalizada], key="sb_exercicio_sel"
            )
            if exercicio_selecionado == opcao_personalizada:
                exercicio_selecionado = st.text_input("Nome do exercício", placeholder="Digite o exercício...")

            col_sets, col_reps = st.columns(2)
            series = col_sets.number_input("Séries", min_value=1, value=3, step=1)
            reps = col_reps.text_input("Reps/Tempo", value="10 a 12")

            url_video = st.text_input("URL do Vídeo (YouTube)", placeholder="https://youtube.com/...")
            observacoes = st.text_area("Orientações / Observações", placeholder="Ex: Manter tronco firme, foco na explosão...")

            if st.button("Adicionar ao Treino", type="primary", use_container_width=True):
                if not exercicio_selecionado.strip():
                    st.error("Digite o nome do exercício.")
                else:
                    novo_treino = {
                        "exercicio": exercicio_selecionado.strip(),
                        "series": series,
                        "reps": reps,
                        "url_video": url_video.strip(),
                        "observacoes": observacoes.strip()
                    }
                    st.session_state.db[aluno_atual]["treinos"].append(novo_treino)
                    atualizar_db()
                    st.success("Exercício adicionado ao plano!")
                    st.rerun()
    else:
        st.markdown("#### ⚡ Meu Treino")
        aluno_atual = aluno_atribuido
        if aluno_atual not in st.session_state.db:
            aluno_atual = None
        if aluno_atual:
            modalidade_aluno = st.session_state.db[aluno_atual].get("modalidade", "Treino")
            st.markdown(f"Modalidade: **{MODALIDADES_ICONES.get(modalidade_aluno, modalidade_aluno)}**")
            total_ex = len(st.session_state.db[aluno_atual].get("treinos", []))
            st.caption(f"Total de exercícios na ficha: **{total_ex}**")

# ==========================================
# ÁREA PRINCIPAL
# ==========================================

# 1. SE NENHUM ALUNO ESTIVER SELECIONADO
if not aluno_atual:
    if eh_admin:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(21, 29, 47, 0.95) 0%, rgba(13, 19, 32, 0.95) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 2rem 1.8rem; margin-bottom: 1.5rem; text-align: center;">
                <span class="kn-chip" style="margin-bottom: 0.8rem;">⚡ PAINEL DO TREINADOR</span>
                <h1 style="margin: 0.3rem 0; font-size: 2.3rem;">Treino bem planejado. Evolução constante.</h1>
                <p style="color: #94a3b8; font-size: 1.05rem; max-width: 720px; margin: 0 auto;">
                    Estruture treinos específicos, monitore a presença e acompanhe a evolução de cada atleta.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        total_alunos = len(st.session_state.db)
        total_treinos_cadastrados = sum(len(dados.get("treinos", [])) for dados in st.session_state.db.values())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Atletas Cadastrados", total_alunos)
        c2.metric("Exercícios no Banco", total_treinos_cadastrados)
        c3.metric("Modalidades Ativas", len(MODALIDADES_EXERCICIOS))

        st.info("👈 Selecione um atleta ou cadastre um novo no menu lateral para visualizar e montar sua rotina.")

        if total_alunos > 0:
            st.markdown("### 📋 Atletas Ativos")
            cols_alunos = st.columns(min(3, max(1, total_alunos)))
            for idx, (nome_al, dados_al) in enumerate(st.session_state.db.items()):
                col_target = cols_alunos[idx % len(cols_alunos)]
                with col_target:
                    with st.container(border=True):
                        st.markdown(f"#### ⚡ {nome_al}")
                        mod = dados_al.get('modalidade', 'Esporte')
                        st.caption(f"Modalidade: **{MODALIDADES_ICONES.get(mod, mod)}**")
                        n_exercicios = len(dados_al.get('treinos', []))
                        st.markdown(f"<span class='kn-chip-cyan'>{n_exercicios} exercícios cadastrados</span>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(21, 29, 47, 0.95) 0%, rgba(13, 19, 32, 0.95) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; padding: 2rem 1.8rem; margin-bottom: 1.5rem; text-align: center;">
                <span class="kn-chip" style="margin-bottom: 0.8rem;">⚡ MEU TREINO</span>
                <h1 style="margin: 0.3rem 0; font-size: 2.3rem;">Olá, {usuario_autenticado} 👋</h1>
                <p style="color: #94a3b8; font-size: 1.05rem; margin: 0;">
                    Seu treino personalizado está sendo preparado pelo treinador.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("Assim que seu treinador liberar sua planilha, seus exercícios e vídeos aparecerão aqui.")

else:
    # 2. ATLETA SELECIONADO: FOTO DO ATLETA EM CIMA DE TUDO E DADOS DO ATLETA EM BAIXO
    dados_aluno = st.session_state.db[aluno_atual]
    treinos = dados_aluno.get("treinos", [])
    modalidade = dados_aluno.get("modalidade", "Treinamento")
    modalidade_formatada = MODALIDADES_ICONES.get(modalidade, modalidade)

    # Recupera os dados de perfil completos do atleta
    perfil_atleta = obter_perfil_atleta(aluno_atual, usuarios)
    peso_val = perfil_atleta.get("peso_kg") if perfil_atleta.get("peso_kg") is not None else perfil_atleta.get("peso")
    altura_val = perfil_atleta.get("altura_cm") if perfil_atleta.get("altura_cm") is not None else perfil_atleta.get("altura")
    idade_val = perfil_atleta.get("idade")
    sexo_val = perfil_atleta.get("sexo", "Não informado")
    foto_val = perfil_atleta.get("foto") or perfil_atleta.get("foto_base64")

    try:
        peso_num = float(peso_val) if peso_val is not None else None
    except (ValueError, TypeError):
        peso_num = None

    try:
        altura_num = float(altura_val) if altura_val is not None else None
    except (ValueError, TypeError):
        altura_num = None

    try:
        idade_num = int(idade_val) if idade_val is not None else None
    except (ValueError, TypeError):
        idade_num = None

    imc_num = calcular_imc(peso_num, altura_num)
    classificacao_imc = "Normal"
    if imc_num is not None:
        if imc_num < 18.5:
            classificacao_imc = "Abaixo do peso"
        elif imc_num < 25:
            classificacao_imc = "Peso ideal"
        elif imc_num < 30:
            classificacao_imc = "Sobrepeso"
        else:
            classificacao_imc = "Obesidade"

    # Prepara a imagem para o st.image de forma segura
    foto_para_exibir = None
    if foto_val and isinstance(foto_val, str):
        if foto_val.startswith("data:image"):
            try:
                raw_b64 = foto_val.split("base64,", 1)[1]
                foto_para_exibir = Image.open(BytesIO(base64.b64decode(raw_b64)))
            except Exception:
                foto_para_exibir = None
        else:
            try:
                foto_para_exibir = Image.open(BytesIO(base64.b64decode(foto_val)))
            except Exception:
                foto_para_exibir = None

    # --- 1. FOTO DO ATLETA EM CIMA DE TUDO ---
    col_e, col_foto_centro, col_d = st.columns([1, 0.8, 1])
    with col_foto_centro:
        if foto_para_exibir is not None:
            with st.container():
                st.markdown('<div class="kn-photo-frame">', unsafe_allow_html=True)
                st.image(foto_para_exibir, width=150)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                """
                <div style="display: flex; justify-content: center;">
                    <div class="kn-athlete-placeholder">👤</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # --- 2. EM BAIXO OS DADOS DO ATLETA ---
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="margin: 0.2rem 0 0.4rem; font-size: 2.3rem; color: #ffffff;">{aluno_atual}</h1>
            <div style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 0.8rem;">
                <span class="kn-chip-cyan">{modalidade_formatada}</span>
                <span class="kn-chip">⚡ Atleta Ativo</span>
            </div>
            <div class="kn-data-grid">
                <div class="kn-data-card">
                    <div class="kn-data-label">⚖️ Peso</div>
                    <div class="kn-data-value">{f"{peso_num:.1f} kg" if peso_num else "--"}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">📏 Altura</div>
                    <div class="kn-data-value">{f"{altura_num:.1f} cm" if altura_num else "--"}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">🎂 Idade</div>
                    <div class="kn-data-value">{f"{idade_num} anos" if idade_num else "--"}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">⚡ IMC</div>
                    <div class="kn-data-value" style="color: #f5c400;">{f"{imc_num:.1f}" if imc_num else "--"}</div>
                    <div style="font-size: 0.72rem; color: #38bdf8; font-weight: 700; margin-top: 2px;">{classificacao_imc if imc_num else ""}</div>
                </div>
                <div class="kn-data-card">
                    <div class="kn-data-label">⚧️ Gênero</div>
                    <div class="kn-data-value" style="font-size: 1rem; padding-top: 3px;">{sexo_val}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Expander retrátil para atualizar foto e dados
    with st.expander(f"⚙️ Atualizar Foto e Dados Corporais de {aluno_atual}", expanded=False):
        col_ed_foto, col_ed_dados = st.columns([1, 2], gap="large")

        with col_ed_foto:
            if foto_para_exibir is not None:
                st.image(foto_para_exibir, width=130, caption=f"Foto Atual de {aluno_atual}")
            else:
                st.caption("Sem foto cadastrada no momento.")

            foto_nova = st.file_uploader(
                "Selecionar Nova Foto",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"upload_foto_{aluno_atual}",
                help="Tamanho máximo recomendado: 300KB"
            )
            remover_foto_atual = st.checkbox("Remover foto", key=f"rem_foto_{aluno_atual}") if foto_para_exibir is not None else False

        with col_ed_dados:
            c_p, c_a = st.columns(2)
            peso_edit = c_p.number_input(
                "Peso (kg)",
                min_value=1.0,
                max_value=350.0,
                value=peso_num if peso_num is not None else 70.0,
                step=0.1,
                format="%.1f",
                key=f"input_peso_{aluno_atual}"
            )
            altura_edit = c_a.number_input(
                "Altura (cm)",
                min_value=50.0,
                max_value=250.0,
                value=altura_num if altura_num is not None else 170.0,
                step=0.5,
                format="%.1f",
                key=f"input_altura_{aluno_atual}"
            )

            c_i, c_s = st.columns(2)
            idade_edit = c_i.number_input(
                "Idade (anos)",
                min_value=1,
                max_value=120,
                value=idade_num if idade_num is not None else 20,
                step=1,
                key=f"input_idade_{aluno_atual}"
            )
            opcoes_genero = ["Não informado", "Feminino", "Masculino", "Outro", "Prefiro não informar"]
            idx_gen = opcoes_genero.index(sexo_val) if sexo_val in opcoes_genero else 0
            sexo_edit = c_s.selectbox(
                "Gênero",
                opcoes_genero,
                index=idx_gen,
                key=f"input_sexo_{aluno_atual}"
            )

            if st.button("Salvar Dados e Foto do Atleta", type="primary", use_container_width=True):
                novo_perfil = {
                    "peso": peso_edit,
                    "peso_kg": peso_edit,
                    "altura": altura_edit,
                    "altura_cm": altura_edit,
                    "idade": idade_edit,
                    "sexo": sexo_edit,
                }
                try:
                    if foto_nova is not None:
                        foto_processada = preparar_foto_perfil(foto_nova)
                        novo_perfil["foto"] = foto_processada
                        novo_perfil["foto_base64"] = foto_processada
                    elif foto_val and not remover_foto_atual:
                        novo_perfil["foto"] = foto_val
                        novo_perfil["foto_base64"] = foto_val
                except Exception as erro:
                    st.error(f"Erro ao salvar foto: {erro}")
                else:
                    if aluno_atual in st.session_state.db:
                        st.session_state.db[aluno_atual]["perfil"] = novo_perfil
                        if eh_admin:
                            atualizar_db()

                    for u_nome, u_reg in usuarios.items():
                        if u_reg.get("aluno") == aluno_atual or u_nome.casefold() == aluno_atual.casefold():
                            u_reg["perfil"] = novo_perfil
                            salvar_usuarios(usuarios)
                            break

                    st.success("Dados do atleta atualizados com sucesso!")
                    st.rerun()

    # --- MÉTRICAS DE TREINO DO ATLETA (KPIS) ---
    total_series = sum(t.get("series", 0) for t in treinos)
    total_videos = sum(bool(t.get("url_video")) for t in treinos)
    faltas = dados_aluno.get("faltas", [])

    if eh_admin:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Exercícios", len(treinos))
        m2.metric("Séries Totais", total_series)
        m3.metric("Vídeos de Apoio", total_videos)
        m4.metric("Faltas Registradas", len(faltas))

        tab_treino, tab_frequencia, tab_analise = st.tabs(
            ["📋 Plano de Treino", "📅 Frequência & Presença", "📈 Análise de Volume"]
        )
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Exercícios", len(treinos))
        m2.metric("Séries Totais", total_series)
        m3.metric("Vídeos de Apoio", total_videos)

        tab_treino, tab_analise = st.tabs(["📋 Meu Treino", "📈 Análise de Volume"])

    # ==========================================
    # TAB 1: FICHA DE TREINO
    # ==========================================
    with tab_treino:
        if not treinos:
            st.markdown(
                """
                <div class="kn-empty-video" style="padding: 3rem 1.5rem;">
                    <span style="font-size: 2.8rem;">📋</span>
                    <h3 style="margin: 0; color: #ffffff;">Ficha de treino vazia</h3>
                    <p style="color: #94a3b8; margin: 0; max-width: 480px;">
                        Nenhum exercício cadastrado ainda. Adicione exercícios pelo menu lateral para montar a rotina.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            for i, treino in enumerate(treinos):
                nome_exercicio = treino['exercicio']
                series = treino['series']
                reps = treino['reps']
                obs = treino.get('observacoes', '').strip()
                url_video = treino.get('url_video', '').strip()

                titulo_expander = f"⚡ {i+1}. {nome_exercicio}  •  {series} Séries  •  {reps}"
                with st.expander(titulo_expander, expanded=True):
                    col_detalhes, col_midia = st.columns([1.1, 1], gap="large")
                    
                    with col_detalhes:
                        st.markdown(
                            f"""
                            <div style="display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
                                <div class="kn-stat-badge">
                                    <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Séries</span>
                                    <span style="font-size: 1.35rem; font-weight: 800; color: #f5c400;">{series}</span>
                                </div>
                                <div class="kn-stat-badge">
                                    <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Volume / Reps</span>
                                    <span style="font-size: 1.35rem; font-weight: 800; color: #ffffff;">{reps}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if obs:
                            st.markdown(
                                f"""
                                <div class="kn-coach-note">
                                    <strong style="color: #f5c400;">💡 Instrução Técnica:</strong><br>
                                    {obs}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        if eh_admin:
                            st.write("")
                            if st.button("🗑️ Remover Exercício", key=f"del_{aluno_atual}_{i}", help="Excluir este exercício do plano"):
                                st.session_state.db[aluno_atual]["treinos"].pop(i)
                                atualizar_db()
                                st.rerun()

                    with col_midia:
                        if url_video:
                            st.markdown("<span style='font-size: 0.85rem; font-weight: 700; color: #cbd5e1;'>🎥 DEMONSTRAÇÃO EM VÍDEO</span>", unsafe_allow_html=True)
                            try:
                                st.video(url_video)
                            except Exception:
                                st.warning("Não foi possível reproduzir o vídeo. Verifique se o link é válido.")
                        else:
                            st.markdown(
                                """
                                <div class="kn-empty-video">
                                    <span style="font-size: 2rem;">🎬</span>
                                    <span style="color: #64748b; font-size: 0.88rem;">Sem vídeo demonstrativo associado</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

    # ==========================================
    # TAB 2: FREQUÊNCIA (APENAS ADMINISTRADOR)
    # ==========================================
    if eh_admin:
        with tab_frequencia:
            faltas = dados_aluno.get("faltas", [])
            mes_atual_str = date.today().strftime("%Y-%m")
            faltas_mes = sum(registro.get("data", "").startswith(mes_atual_str) for registro in faltas)

            rf1, rf2 = st.columns(2)
            rf1.metric("Total de Faltas Registradas", len(faltas))
            rf2.metric("Faltas Neste Mês", faltas_mes)

            st.write("")
            col_cadastrar_falta, col_historico_falta = st.columns([1, 1.3], gap="large")

            with col_cadastrar_falta:
                with st.container(border=True):
                    st.markdown("#### 📝 Registrar Falta")
                    st.caption(f"Controle de presença de **{aluno_atual}** (visível somente ao treinador).")
                    with st.form(f"form_falta_{aluno_atual}"):
                        data_falta = st.date_input("Data da Ausência", value=date.today())
                        motivo_falta = st.text_area(
                            "Motivo ou Observação (Opcional)",
                            placeholder="Ex.: Avisou com antecedência / lesão leve no joelho",
                        )
                        btn_registrar_falta = st.form_submit_button("Registrar Falta", type="primary", use_container_width=True)

                    if btn_registrar_falta:
                        dados_aluno.setdefault("faltas", []).append(
                            {
                                "data": data_falta.isoformat(),
                                "motivo": motivo_falta.strip(),
                            }
                        )
                        atualizar_db()
                        st.success("Falta registrada com sucesso!")
                        st.rerun()

            with col_historico_falta:
                st.markdown("#### 📅 Histórico de Ausências")
                if not faltas:
                    st.markdown(
                        """
                        <div class="kn-success-card">
                            <span style="font-size: 2.2rem;">🏆</span>
                            <div>
                                <h4 style="margin: 0; color: #10b981;">Frequência Impecável!</h4>
                                <p style="margin: 4px 0 0; color: #94a3b8; font-size: 0.9rem;">
                                    Nenhuma falta registrada para este atleta.
                                </p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    for indice, registro in sorted(
                        enumerate(faltas),
                        key=lambda item: item[1].get("data", ""),
                        reverse=True,
                    ):
                        with st.container(border=True):
                            c_data, c_mot, c_del = st.columns([1, 2.2, 0.8], vertical_alignment="center")
                            with c_data:
                                try:
                                    data_formatada = date.fromisoformat(registro['data']).strftime('%d/%m/%Y')
                                except Exception:
                                    data_formatada = registro.get('data', '--')
                                st.markdown(f"**🗓️ {data_formatada}**")
                            with c_mot:
                                st.write(registro.get("motivo") or "Motivo não informado.")
                            with c_del:
                                if st.button("Excluir", key=f"del_falta_{aluno_atual}_{indice}", use_container_width=True):
                                    faltas.pop(indice)
                                    atualizar_db()
                                    st.rerun()

    # ==========================================
    # TAB 3: ANÁLISE DE VOLUME E GRÁFICOS
    # ==========================================
    with tab_analise:
        if not treinos:
            st.info("Cadastre exercícios no plano para visualizar a análise gráfica de volume.")
        else:
            df_treinos = pd.DataFrame(treinos)
            col_g1, col_g2 = st.columns(2, gap="large")

            with col_g1:
                with st.container(border=True):
                    st.markdown("#### 🎯 Distribuição dos Exercícios")
                    st.caption("Proporção de cada fundamento dentro do plano de treino.")
                    fig_donut = plot_distribuicao_exercicios(df_treinos)
                    st.pyplot(fig_donut)

            with col_g2:
                with st.container(border=True):
                    st.markdown("#### ⚡ Volume de Treino (Séries Totais)")
                    st.caption("Carga planejada em número total de séries por exercício.")
                    fig_bar = plot_volume_series(df_treinos)
                    st.pyplot(fig_bar)
