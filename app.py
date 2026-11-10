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

# Estilo CSS customizado para destacar os menus, touchscreen e pódio olímpico
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
        .podio-container {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border: 2px solid #cbd5e1;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .podio-ouro {
            background-color: #fef08a;
            border-left: 6px solid #eab308;
            padding: 10px 15px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        }
        .podio-prata {
            background-color: #f1f5f9;
            border-left: 6px solid #94a3b8;
            padding: 10px 15px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        }
        .podio-bronze {
            background-color: #ffedd5;
            border-left: 6px solid #f97316;
            padding: 10px 15px;
            border-radius: 8px;
            margin: 8px 0;
            font-weight: bold;
        }
        @media (prefers-color-scheme: dark) {
            div[role="radiogroup"] label {
                background-color: #262730;
            }
            .dupla-card {
                background-color: #1e1e1e;
                border: 1px solid #333;
            }
            .podio-container {
                background: linear-gradient(135deg, #1e1e1e, #111827);
                border: 2px solid #374151;
            }
            .podio-ouro {
                background-color: #422006;
                color: #fde047;
            }
            .podio-prata {
                background-color: #1e293b;
                color: #cbd5e1;
            }
            .podio-bronze {
                background-color: #431407;
                color: #fdba74;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Verificação inicial de pacotes essenciais
if not PYMONGO_INSTALADO:
    st.error("⚠ O pacote `pymongo` não está instalado no ambiente!")
    st.stop()

if not REPORTLAB_INSTALADO:
    st.error("⚠ O pacote `reportlab` não está instalado no ambiente!")
    st.stop()

# --- TELA DE BOAS-VINDAS (SPLASH SCREEN - 3 SEGUNDOS) ---
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
    time.sleep(3)
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
                pass
        return True
    return False

def deletar_turma(nome_turma):
    global db
    if nome_turma in st.session_state.cache_offline_turmas:
        st.session_state.cache_offline_turmas.remove(nome_turma)
    if db is not None:
        try:
            db["turmas"].delete_one({"nome": nome_turma})
        except Exception:
            pass

def carregar_alunos():
    global db
    if db is not None:
        try:
            alunos_docs = list(db["alunos"].find({}, {"_id": 0}))
            if alunos_docs:
                st.session_state.cache_offline_alunos = alunos_docs
        except Exception:
            pass
    return st.session_state.cache_offline_alunos

def cadastrar_aluno(nome, turma):
    global db
    novo = {"nome": nome, "turma": turma}
    st.session_state.cache_offline_alunos.append(novo)
    if db is not None:
        try:
            db["alunos"].insert_one(novo)
        except Exception:
            pass

def deletar_aluno(nome, turma):
    global db
    st.session_state.cache_offline_alunos = [a for a in st.session_state.cache_offline_alunos if not (a["nome"] == nome and a["turma"] == turma)]
    if db is not None:
        try:
            db["alunos"].delete_one({"nome": nome, "turma": turma})
        except Exception:
            pass

def carregar_confrontos(turma, modalidade, fase):
    global db
    chave = f"{turma}_{modalidade}_{fase}"
    if db is not None:
        try:
            doc = db["confrontos"].find_one({"turma": turma, "modalidade": modalidade, "fase": fase})
            if doc:
                st.session_state.cache_offline_confrontos[chave] = doc["confrontos"]
        except Exception:
            pass
    return st.session_state.cache_offline_confrontos.get(chave, [])

def salvar_confrontos(turma, modalidade, fase, lista_confrontos):
    global db
    chave = f"{turma}_{modalidade}_{fase}"
    st.session_state.cache_offline_confrontos[chave] = lista_confrontos
    if db is not None:
        try:
            db["confrontos"].update_one(
                {"turma": turma, "modalidade": modalidade, "fase": fase},
                {"$set": {"turma": turma, "modalidade": modalidade, "fase": fase, "confrontos": lista_confrontos}},
                upsert=True
            )
        except Exception:
            pass

def resetar_torneio_turma(turma, modalidade):
    global db
    chaves_remover = [k for k in st.session_state.cache_offline_confrontos.keys() if k.startswith(f"{turma}_{modalidade}_")]
    for k in chaves_remover:
        del st.session_state.cache_offline_confrontos[k]
    if db is not None:
        try:
            db["confrontos"].delete_many({"turma": turma, "modalidade": modalidade})
        except Exception:
            pass

def salvar_podio(turma, modalidade, podio_dict, responsavel=""):
    global db
    podio_limpo = {
        "1º": podio_dict.get("1º", "A definir"),
        "2º": podio_dict.get("2º", "A definir"),
        "3º": podio_dict.get("3º", "A definir")
    }
    registro = {"turma": turma, "modalidade": modalidade, "podio": podio_limpo, "responsavel": responsavel}
    st.session_state.cache_offline_historico = [h for h in st.session_state.cache_offline_historico if not (h["turma"] == turma and h["modalidade"] == modalidade)]
    st.session_state.cache_offline_historico.append(registro)
    
    if db is not None:
        try:
            db["historico_podio"].update_one(
                {"turma": turma, "modalidade": modalidade},
                {"$set": registro},
                upsert=True
            )
        except Exception:
            pass

def carregar_historico():
    global db
    if db is not None:
        try:
            hist_docs = list(db["historico_podio"].find({}, {"_id": 0}))
            if hist_docs:
                st.session_state.cache_offline_historico = hist_docs
        except Exception:
            pass
    return st.session_state.cache_offline_historico

def resetar_historico():
    global db
    st.session_state.cache_offline_historico = []
    if db is not None:
        try:
            db["historico_podio"].delete_many({})
        except Exception:
            pass

def gerar_pdf_relatorio_completo(historico_dados, nome_torneio):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=15, textColor=colors.HexColor('#1E3A8A')
    )
    
    story.append(Paragraph(f"<b>{nome_torneio.upper()}</b>", title_style))
    story.append(Paragraph("<b>Relatório Oficial de Campeões & Chaveamentos</b>", ParagraphStyle('Sub', parent=styles['Normal'], alignment=1, fontSize=11, spaceAfter=15)))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Resumo dos Pódios por Turma e Modalidade</b>", styles['Heading2']))
    tabela_dados = [["Modalidade", "Turma", "Responsável", "1º Lugar (Ouro)", "2º Lugar (Prata)", "3º Lugar (Bronze)"]]
    for h in historico_dados:
        mod = h.get("modalidade", "Jogo").upper()
        turma = h.get("turma", "Geral")
        resp = h.get("responsavel", "Não informado")
        podio = h.get("podio", {})
        tabela_dados.append([mod, turma, resp, podio.get("1º", "A definir"), podio.get("2º", "A definir"), podio.get("3º", "A definir")])

    t = Table(tabela_dados, colWidths=[70, 70, 90, 100, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
    ]))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 10px 0px 5px 0px;">
            <span style="font-size: 42px;">🏆</span>
            <h3 style="margin: 0px; color: #2563eb;">TORNEIO ESCOLAR</h3>
            <p style="font-size: 11px; color: gray; margin-top: 2px;">Gestão Oficial de Jogos de Tabuleiro</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.header("⚙️ Configurações & Gestão")
    nome_torneio = st.text_input("Nome do Torneio:", "Torneio de Jogos Escolares")
    professor_responsavel = st.text_input("👨‍🏫 Professor Responsável:", "Professor(a)")
    modo_projetor = st.checkbox("📽️ Ativar Modo Tela Cheia / Projetor", value=False)
    
    st.divider()
    st.subheader("💾 Backup & Restauração")
    dados_backup = {
        "turmas": carregar_turmas(),
        "alunos": carregar_alunos(),
        "historico": carregar_historico(),
        "confrontos": st.session_state.cache_offline_confrontos
    }
    st.download_button(
        label="📥 Baixar Backup (JSON)",
        data=json.dumps(dados_backup, ensure_ascii=False, indent=4),
        file_name="backup_torneio.json",
        mime="application/json",
        use_container_width=True
    )
    
    arquivo_subido = st.file_uploader("📤 Restaurar Backup", type=["json"])
    if arquivo_subido is not None:
        try:
            conteudo_json = json.load(arquivo_subido)
            if "turmas" in conteudo_json:
                st.session_state.cache_offline_turmas = conteudo_json["turmas"]
            if "alunos" in conteudo_json:
                st.session_state.cache_offline_alunos = conteudo_json["alunos"]
            if "historico" in conteudo_json:
                st.session_state.cache_offline_historico = conteudo_json["historico"]
            if "confrontos" in conteudo_json:
                st.session_state.cache_offline_confrontos = conteudo_json["confrontos"]
            st.success("✅ Backup restaurado com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.divider()
    st.subheader("🏫 Gerenciar Turmas")
    nova_turma_input = st.text_input("Nome da Turma (Ex: 1º Ano A):", key="cad_turma_nova")
    if st.button("➕ Adicionar Turma", use_container_width=True):
        if nova_turma_input.strip():
            if cadastrar_turma(nova_turma_input.strip()):
                st.toast(f"✅ Turma cadastrada!", icon="🎉")
                st.rerun()
            else:
                st.warning("Esta turma já está cadastrada.")
        else:
            st.warning("Digite o nome da turma.")

    turmas_atuais = carregar_turmas()
    if turmas_atuais:
        turma_a_remover = st.selectbox("Remover Turma:", ["Selecione..."] + turmas_atuais, key="sel_rem_turma")
        if st.button("🗑️ Excluir Turma", use_container_width=True):
            if turma_a_remover != "Selecione...":
                deletar_turma(turma_a_remover)
                st.toast(f"🗑️ Turma removida.", icon="⚠️")
                st.rerun()

    st.divider()
    st.markdown("<p style='text-align: center; font-size: 13px; color: gray;'>Desenvolvido por <b>Sérgio Santos</b></p>", unsafe_allow_html=True)

if modo_projetor:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

def processar_avanco_fase(turma, modalidade, fase_atual, confrontos_fase, vencedores, responsavel):
    salvar_confrontos(turma, modalidade, fase_atual, [{**c, "vencedor": vencedores[i]} for i, c in enumerate(confrontos_fase)])

    if len(vencedores) == 1:
        primeiro = vencedores[0]
        partida_final = confrontos_fase[0]
        segundo = partida_final["j2"] if partida_final["j1"] == primeiro else partida_final["j1"]
        if segundo == "BYE (Passa direto)":
            segundo = "Sem vice-campeão"

        terceiro = "A definir"
        if fase_atual > 1:
            fase_anterior = carregar_confrontos(turma, modalidade, fase_atual - 1)
            perdedores_semi = []
            for conf in fase_anterior:
                venc = conf.get("vencedor")
                j1_prev, j2_prev = conf.get("j1"), conf.get("j2")
                if venc and j2_prev != "BYE (Passa direto)":
                    perdedor = j2_prev if venc == j1_prev else j1_prev
                    if perdedor not in [primeiro, segundo]:
                        perdedores_semi.append(perdedor)
            if perdedores_semi:
                terceiro = ", ".join(perdedores_semi)

        salvar_podio(turma, modalidade, {"1º": primeiro, "2º": segundo, "3º": terceiro}, responsavel)
        salvar_confrontos(turma, modalidade, fase_atual + 1, [{"j1": primeiro, "j2": None, "vencedor
