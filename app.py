import random
import time
import io
import json
import streamlit as st

# --- TRATAMENTO DE IMPORTAÇÕES ---
try:
    from pymongo import MongoClient
    PYMONGO_INSTALADO = True
except ImportError:
    PYMONGO_INSTALADO = False

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_INSTALADO = True
except ImportError:
    AUTOREFRESH_INSTALADO = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_INSTALADO = True
except ImportError:
    REPORTLAB_INSTALADO = False

# --- CONFIGURAÇÃO DE PÁGINA (RESPONSIVO PARA MOBILE, TABLET E PC) ---
st.set_page_config(
    page_title="Torneio de Jogos de Tabuleiro Escolar",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo CSS customizado para destacar os menus, touchscreen e relógio
st.markdown("""
    <style>
        button[data-baseweb="tab"] {
            font-size: 18px !important;
            font-weight: 900 !important;
            letter-spacing: 1px;
            padding: 10px 16px !important;
        }
        .stButton>button {
            width: 100%;
            height: 3em;
            font-size: 16px !important;
            font-weight: bold;
            border-radius: 8px;
        }
        div[role="radiogroup"] label {
            padding: 8px 12px;
            background-color: #f0f2f6;
            border-radius: 8px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
        }
        .dupla-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        @media (prefers-color-scheme: dark) {
            div[role="radiogroup"] label {
                background-color: #262730;
            }
            .dupla-card {
                background-color: #1e1e1e;
                border: 1px solid #333;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Verificação inicial de pacotes essenciais
if not PYMONGO_INSTALADO:
    st.error("⚠ O pacote `pymongo` não está instalado no ambiente!")
    st.stop()

if not AUTOREFRESH_INSTALADO:
    st.error("⚠ O pacote `streamlit-autorefresh` não está instalado no ambiente!")
    st.stop()

if not REPORTLAB_INSTALADO:
    st.error("⚠ O pacote `reportlab` não está instalado no ambiente!")
    st.stop()

# --- TELA DE BOAS-VINDAS (SPLASH SCREEN - 5 SEGUNDOS) ---
if "splash_done" not in st.session_state:
    st.session_state.splash_done = False

if not st.session_state.splash_done:
    placeholder_splash = st.empty()
    with placeholder_splash.container():
        st.markdown(
            """
            <div style="text-align: center; padding: 50px 20px; background: linear-gradient(135deg, #1e3a8a, #2563eb); border-radius: 15px; color: white; margin-top: 50px; box-shadow: 0 10px 25px rgba(0,0,0,0.2);">
                <h1>♟️ Torneio de Jogos de Tabuleiro Escolar</h1>
                <h3 style="margin-top: 15px; font-weight: 300;">Bem-vindo(a) ao sistema oficial de gestão de campeonatos</h3>
                <p style="margin-top: 30px; font-size: 16px; opacity: 0.8;">Carregando o ambiente do torneio em instantes...</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    time.sleep(5)
    placeholder_splash.empty()
    st.session_state.splash_done = True
    st.rerun()

# --- CONEXÃO COM O MONGODB E SUPORTE OFFLINE / CACHE LOCAL ---
MONGO_URI = st.secrets.get("MONGO_URI", "")

@st.cache_resource
def get_database():
    if not MONGO_URI:
        return None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        return client["torneio_escolar"]
    except Exception:
        return None

db = get_database()

# Inicialização do Cache Local de Segurança (Operação Offline)
if "cache_offline_turmas" not in st.session_state:
    st.session_state.cache_offline_turmas = ["1º Ano A", "1º Ano B", "2º Ano A", "3º Ano A", "4º Ano A", "5º Ano A"]
if "cache_offline_alunos" not in st.session_state:
    st.session_state.cache_offline_alunos = []
if "cache_offline_confrontos" not in st.session_state:
    st.session_state.cache_offline_confrontos = {}
if "cache_offline_historico" not in st.session_state:
    st.session_state.cache_offline_historico = []

# --- FUNÇÕES DE BANCO DE DADOS HÍBRIDAS (ONLINE/OFFLINE) ---
def carregar_turmas():
    global db
    if db is not None:
        try:
            turmas_docs = list(db["turmas"].find({}, {"_id": 0}))
            if turmas_docs:
                st.session_state.cache_offline_turmas = [t["nome"] for t in turmas_docs]
            else:
                for t in st.session_state.cache_offline_turmas:
                    db["turmas"].update_one({"nome": t}, {"$set": {"nome": t}}, upsert=True)
        except Exception:
            pass
    return st.session_state.cache_offline_turmas

def cadastrar_turma(nome_turma):
    global db
    if nome_turma not in st.session_state.cache_offline_turmas:
        st.session_state.cache_offline_turmas.append(nome_turma)
        if db is not None:
            try:
                db["turmas"].update_one({"nome": nome_turma}, {"$set": {"nome": nome_turma}}, upsert=True)
            except Exception:
