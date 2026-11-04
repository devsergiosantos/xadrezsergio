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

def atualizar_aluno_turma(nome_antigo, turma_antiga, novo_nome, nova_turma):
    global db
    for a in st.session_state.cache_offline_alunos:
        if a["nome"] == nome_antigo and a["turma"] == turma_antiga:
            a["nome"] = novo_nome
            a["turma"] = nova_turma
            break
    if db is not None:
        try:
            db["alunos"].update_one(
                {"nome": nome_antigo, "turma": turma_antiga},
                {"$set": {"nome": novo_nome, "turma": nova_turma}}
            )
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

# --- FUNÇÃO PARA GERAR PDF COMPLETO (RELATÓRIO + PÓDIO) ---
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

# --- ESTADO DO TEMPORIZADOR ---
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "seconds_remaining" not in st.session_state:
    st.session_state.seconds_remaining = 300
if "last_tick" not in st.session_state:
    st.session_state.last_tick = time.time()
if "timer_expanded" not in st.session_state:
    st.session_state.timer_expanded = False

if st.session_state.timer_running:
    agora = time.time()
    passado = int(agora - st.session_state.last_tick)
    if passado > 0:
        st.session_state.seconds_remaining = max(0, st.session_state.seconds_remaining - passado)
        st.session_state.last_tick = agora
        if st.session_state.seconds_remaining == 0:
            st.session_state.timer_running = False
    st_autorefresh(interval=1000, key="relogio_counter")

# --- BARRA LATERAL (MENU, BACKUP, PROJEÇÃO E IDENTIFICAÇÃO DO PROFESSOR) ---
with st.sidebar:
    st.header("⚙️ Configurações & Gestão")
    nome_torneio = st.text_input("Nome do Torneio:", "Torneio de Jogos Escolares")
    
    professor_responsavel = st.text_input("👨‍🏫 Professor Responsável:", "Professor(a)", help="Nome do professor que está operando o torneio neste momento.")
    
    modo_projetor = st.checkbox("📽️ Ativar Modo Tela Cheia / Projetor", value=False, help="Oculta esta barra lateral para maximizar o espaço na lousa/projetor.")
    
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

# --- RELÓGIO LATERAL ---
def renderizar_relogio_lateral():
    with st.container():
        st.markdown("### ⏱️ Relógio de Partida")
        if st.session_state.timer_expanded:
            font_size = "60px"
            container_bg = "#262730" if st.get_option("theme.base") == "dark" else "#f0f2f6"
        else:
            font_size = "28px"
            container_bg = "transparent"

        mins, secs = divmod(st.session_state.seconds_remaining, 60)
        cor_texto = "#ff4b4b" if st.session_state.seconds_remaining == 0 else "inherit"

        st.markdown(
            f"""<div style="text-align: center; padding: 10px; background-color: {container_bg}; border-radius: 10px;">
                <span style="font-size: {font_size}; font-weight: bold; color: {cor_texto};">{mins:02d}:{secs:02d}</span>
            </div>""",
            unsafe_allow_html=True
        )

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if not st.session_state.timer_running:
                if st.button("▶️ Iniciar", key="btn_start_global", use_container_width=True):
                    st.session_state.timer_running = True
                    st.session_state.last_tick = time.time()
                    st.rerun()
            else:
                if st.button("⏸️ Pausar", key="btn_pause_global", use_container_width=True):
                    st.session_state.timer_running = False
                    st.rerun()
        with col_e2:
            if st.button("🔍 Zoom", key="btn_zoom_global", use_container_width=True):
                st.session_state.timer_expanded = not st.session_state.timer_expanded
                st.rerun()

        tempo_min = st.number_input("Ajustar minutos:", min_value=1, max_value=60, value=5, step=1, key="input_min_relogio")
        if st.button("🔄 Definir Tempo", use_container_width=True):
            st.session_state.seconds_remaining = tempo_min * 60
            st.session_state.timer_running = False
            st.rerun()

# --- FUNÇÃO AUXILIAR DE AVANÇO DE FASE VIA BOTÃO ---
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
        salvar_confrontos(turma, modalidade, fase_atual + 1, [{"j1": primeiro, "j2": None, "vencedor": primeiro}])
        st.balloons()
    else:
        novos_confrontos = []
        random.shuffle(vencedores)
        for i in range(0, len(vencedores), 2):
            if i + 1 < len(vencedores):
                novos_confrontos.append({"j1": vencedores[i], "j2": vencedores[i+1], "vencedor": None})
            else:
                novos_confrontos.append({"j1": vencedores[i], "j2": "BYE (Passa direto)", "vencedor": vencedores[i]})
        salvar_confrontos(turma, modalidade, fase_atual + 1, novos_confrontos)

# --- INTERFACE PRINCIPAL ---
st.title(f"♟️ {nome_torneio}")

# --- DESCRIÇÃO DO APLICATIVO ---
st.markdown("""
> **Sobre o Aplicativo:** Sistema interativo e robusto desenvolvido para o gerenciamento completo de torneios de jogos de tabuleiro escolares (Xadrez, Dama e Dominó). Conta com sorteio automatizado de chaves, relógio de partida integrado, avanço dinâmico de fases, histórico de pódios com exportação em PDF, além de suporte total a operação offline e sincronização em nuvem.
""")

if professor_responsavel.strip():
    st.caption(f"👤 **Organizador(a) / Professor(a) atual:** {professor_responsavel}")

tab_xadrez, tab_dama, tab_domino, tab_historico, tab_alunos = st.tabs([
    "⚔️ XADREZ", "👑 DAMA", "🀄 DOMINÓ", "🏆 HISTÓRICO", "👥 ALUNOS"
])

# ==========================================
# ABA 1: XADREZ
# ==========================================
with tab_xadrez:
    col_relogio_esq, col_conteudo_dir = st.columns([1, 3])
    with col_relogio_esq:
        renderizar_relogio_lateral()
    with col_conteudo_dir:
        st.markdown("## ⚔️ **MODALIDADE: XADREZ**")
        alunos_db = carregar_alunos()
        turmas_disponiveis = carregar_turmas()

        if not turmas_disponiveis:
            st.info("👋 Nenhuma turma cadastrada.")
        else:
            turma_selecionada = st.selectbox("🎯 Selecione a Turma:", turmas_disponiveis, key="turma_xadrez")
            pontos_por_vitoria = st.radio("🏅 Pontuação por vitória:", [2, 10], horizontal=True, key="pts_xadrez")
            
            alunos_filtrados = [a["nome"] for a in alunos_db if a["turma"] == turma_selecionada]
            st.caption(f"Total de alunos na turma **{turma_selecionada}**: {len(alunos_filtrados)}")

            col_sort, col_res = st.columns(2)
            with col_sort:
                btn_iniciar = st.button("🎲 Sortear Fase 1 (XADREZ)", type="primary", use_container_width=True, key="sort_x")
            with col_res:
                btn_limpar = st.button("🗑️ Reiniciar Torneio", use_container_width=True, key="limp_x")

            if btn_iniciar:
                if len(alunos_filtrados) < 2:
                    st.error("É necessário ter pelo menos 2 alunos cadastrados.")
                else:
                    resetar_torneio_turma(turma_selecionada, "Xadrez")
                    jogadores = alunos_filtrados.copy()
                    random.shuffle(jogadores)
                    confrontos = []
                    for i in range(0, len(jogadores), 2):
                        if i + 1 < len(jogadores):
                            confrontos.append({"j1": jogadores[i], "j2": jogadores[i+1], "vencedor": None})
                        else:
                            confrontos.append({"j1": jogadores[i], "j2": "BYE (Passa direto)", "vencedor": jogadores[i]})
                    salvar_confrontos(turma_selecionada, "Xadrez", 1, confrontos)
                    st.rerun()

            if btn_limpar:
                resetar_torneio_turma(turma_selecionada, "Xadrez")
                st.toast("Torneio de Xadrez zerado.", icon="🧹")
                st.rerun()

            fases_registradas = sorted(list(set([int(k.split("_")[-1]) for k in st.session_state.cache_offline_confrontos.keys() if k.startswith(f"{turma_selecionada}_Xadrez_")])), reverse=True)
            fase_atual = fases_registradas[0] if fases_registradas else 1
            confrontos_fase = carregar_confrontos(turma_selecionada, "Xadrez", fase_atual)

            st.divider()
            if confrontos_fase:
                st.markdown(f"#### 🚩 Fase {fase_atual} - XADREZ ({turma_selecionada})")
                if len(confrontos_fase) == 1 and confrontos_fase[0]["j2"] is None:
                    campeao = confrontos_fase[0]['j1']
                    st.success(f"🏆 **CAMPEÃO DE XADREZ DO {turma_selecionada.upper()}: {campeao}** 🏆")
                else:
                    vencedores = []
                    todos_selecionados = True
                    for idx, c in enumerate(confrontos_fase):
                        st.markdown(f"""<div class="dupla-card"><b>Partida {idx + 1} (XADREZ)</b></div>""", unsafe_allow_html=True)
                        j1, j2 = c["j1"], c["j2"]
                        if j2 == "BYE (Passa direto)":
                            st.info(f"⚪ **{j1}** avança automaticamente.")
                            vencedores.append(j1)
                        else:
                            opcoes = ["Selecione...", j1, j2]
                            index_padrao = opcoes.index(c["vencedor"]) if c.get("vencedor") in opcoes else 0
                            escolha = st.selectbox(f"Vencedor da Partida {idx + 1}:", opcoes, index=index_padrao, key=f"px_{fase_atual}_{idx}")
                            if escolha != "Selecione...":
                                vencedores.append(escolha)
                            else:
                                todos_selecionados = False

                    st.write("")
                    if st.button("➡️ Avançar para Próxima Fase (XADREZ)", type="primary", use_container_width=True, key="btn_avancar_xadrez"):
                        if not todos_selecionados or len(vencedores) != len(confrontos_fase):
                            st.error("⚠️ Selecione o vencedor de **todas** as partidas antes de avançar.")
                        else:
                            processar_avanco_fase(turma_selecionada, "Xadrez", fase_atual, confrontos_fase, vencedores, professor_responsavel)
                            st.toast("⚡ Avanço para a próxima fase realizado!", icon="🚀")
                            st.rerun()

# ==========================================
# ABA 2: DAMA
# ==========================================
with tab_dama:
    st.markdown("## 👑 **MODALIDADE: DAMA**")
    alunos_db = carregar_alunos()
    turmas_dama = carregar_turmas()
    if not turmas_dama:
        st.info("👋 Cadastre turmas.")
    else:
        turma_dama_sel = st.selectbox("🎯 Selecione a Turma:", turmas_dama, key="turma_dama")
        pts_dama = st.radio("🏅 Pontuação por vitória:", [2, 10], horizontal=True, key="pts_dama")
        alunos_dama_filtrados = [a["nome"] for a in alunos_db if a["turma"] == turma_dama_sel]

        col_sd1, col_sd2 = st.columns(2)
        with col_sd1:
            btn_sort_dama = st.button("🎲 Sortear Partidas de DAMA", type="primary", use_container_width=True)
        with col_sd2:
            btn_limp_dama = st.button("🗑️ Reiniciar DAMA", use_container_width=True)

        if btn_sort_dama:
            if len(alunos_dama_filtrados) < 2:
                st.error("São necessários pelo menos 2 alunos.")
            else:
                resetar_torneio_turma(turma_dama_sel, "Dama")
                jogadores = alunos_dama_filtrados.copy()
                random.shuffle(jogadores)
                confrontos = []
                for i in range(0, len(jogadores), 2):
                    if i + 1 < len(jogadores):
                        confrontos.append({"j1": jogadores[i], "j2": jogadores[i+1], "vencedor": None})
                    else:
                        confrontos.append({"j1": jogadores[i], "j2": "BYE (Passa direto)", "vencedor": jogadores[i]})
                salvar_confrontos(turma_dama_sel, "Dama", 1, confrontos)
                st.rerun()

        if btn_limp_dama:
            resetar_torneio_turma(turma_dama_sel, "Dama")
            st.rerun()

        fases_dama = sorted(list(set([int(k.split("_")[-1]) for k in st.session_state.cache_offline_confrontos.keys() if k.startswith(f"{turma_dama_sel}_Dama_")])), reverse=True)
        fase_dama_atual = fases_dama[0] if fases_dama else 1
        confs_dama = carregar_confrontos(turma_dama_sel, "Dama", fase_dama_atual)

        if confs_dama:
            st.markdown(f"#### Fase {fase_dama_atual} - DAMA ({turma_dama_sel})")
            if len(confs_dama) == 1 and confs_dama[0].get("j2") is None:
                campeao_dama = confs_dama[0]["j1"]
                st.success(f"🏆 **CAMPEÃO DE DAMA: {campeao_dama}** 🏆")
            else:
                vencedores_dama = []
                todos_ok = True
                for idx, c in enumerate(confs_dama):
                    st.markdown(f"""<div class="dupla-card"><b>Partida DAMA {idx + 1}</b></div>""", unsafe_allow_html=True)
                    j1, j2 = c["j1"], c["j2"]
                    if j2 == "BYE (Passa direto)":
                        st.info(f"⚪ **{j1}** avança automaticamente.")
                        vencedores_dama.append(j1)
                    else:
                        opcoes = ["Selecione...", j1, j2]
                        index_padrao = opcoes.index(c["vencedor"]) if c.get("vencedor") in opcoes else 0
                        escolha = st.selectbox(f"Vencedor da Partida {idx + 1}:", opcoes, index=index_padrao, key=f"pd_{idx}")
                        if escolha != "Selecione...":
                            vencedores_dama.append(escolha)
                        else:
                            todos_ok = False

                st.write("")
                if st.button("➡️ Avançar para Próxima Fase (DAMA)", type="primary", use_container_width=True, key="btn_avancar_dama"):
                    if not todos_ok or len(vencedores_dama) != len(confs_dama):
                        st.error("⚠️ Selecione o vencedor de **todas** as partidas antes de avançar.")
                    else:
                        processar_avanco_fase(turma_dama_sel, "Dama", fase_dama_atual, confs_dama, vencedores_dama, professor_responsavel)
                        st.toast("⚡ Avanço de Dama realizado!", icon="🚀")
                        st.rerun()

# ==========================================
# ABA 3: DOMINÓ
# ==========================================
with tab_domino:
    st.markdown("## 🀄 **MODALIDADE: DOMINÓ**")
    alunos_db = carregar_alunos()
    turmas_domino = carregar_turmas()
    if not turmas_domino:
        st.info("👋 Cadastre turmas.")
    else:
        turma_dom_sel = st.selectbox("🎯 Selecione a Turma:", turmas_domino, key="turma_dom")
        tamanho_mesa = st.selectbox("👥 Alunos por Mesa:", [2, 3, 4], key="tam_mesa_dom")
        pts_dom = st.radio("🏅 Pontuação por vitória:", [2, 10], horizontal=True, key="pts_dom")
        
        alunos_dom_filtrados = [a["nome"] for a in alunos_db if a["turma"] == turma_dom_sel]
        col_dom1, col_dom2 = st.columns(2)
        with col_dom1:
            btn_sort_dom = st.button("🎲 Sortear Mesas de DOMINÓ", type="primary", use_container_width=True)
        with col_dom2:
            btn_limp_dom = st.button("🗑️ Reiniciar DOMINÓ", use_container_width=True)

        if btn_sort_dom:
            if len(alunos_dom_filtrados) < tamanho_mesa:
                st.error(f"São necessários pelo menos {tamanho_mesa} alunos.")
            else:
                resetar_torneio_turma(turma_dom_sel, "Dominó")
                jogadores = alunos_dom_filtrados.copy()
                random.shuffle(jogadores)
                mesas = [{"jogadores": jogadores[i:i + tamanho_mesa], "vencedor": None} for i in range(0, len(jogadores), tamanho_mesa)]
                salvar_confrontos(turma_dom_sel, "Dominó", 1, mesas)
                st.rerun()

        if btn_limp_dom:
            resetar_torneio_turma(turma_dom_sel, "Dominó")
            st.rerun()

        fases_dom = sorted(list(set([int(k.split("_")[-1]) for k in st.session_state.cache_offline_confrontos.keys() if k.startswith(f"{turma_dom_sel}_Dominó_")])), reverse=True)
        fase_dom_atual = fases_dom[0] if fases_dom else 1
        confs_dom = carregar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual)

        if confs_dom:
            st.markdown(f"#### Fase {fase_dom_atual} - DOMINÓ ({turma_dom_sel})")
            lista_mesas_normalizada = []
            for m in confs_dom:
                participantes = m["jogadores"] if "jogadores" in m else [m.get("j1"), m.get("j2")]
                lista_mesas_normalizada.append({"participantes": [p for p in participantes if p and p != "BYE (Passa direto)"], "vencedor": m.get("vencedor")})

            if len(lista_mesas_normalizada) == 1 and len(lista_mesas_normalizada[0]["participantes"]) == 1:
                campeao_domino = lista_mesas_normalizada[0]["participantes"][0]
                st.success(f"🏆 **GRANDE CAMPEÃO DE DOMINÓ: {campeao_domino}** 🏆")
            else:
                vencedores_dom = []
                todos_ok_dom = True
                for idx, m in enumerate(lista_mesas_normalizada):
                    part_str = ', '.join([str(p) for p in m['participantes']])
                    st.markdown(f"""<div class="dupla-card"><b>Mesa {idx + 1} (DOMINÓ)</b> (Participantes: {part_str})</div>""", unsafe_allow_html=True)
                    opcoes = ["Selecione o vencedor..."] + m["participantes"]
                    index_padrao = opcoes.index(m["vencedor"]) if m.get("vencedor") in opcoes else 0
                    escolha = st.selectbox(f"Vencedor da Mesa {idx + 1}:", opcoes, index=index_padrao, key=f"pdom_{fase_dom_atual}_{idx}")
                    if escolha != "Selecione o vencedor...":
                        vencedores_dom.append(escolha)
                    else:
                        todos_ok_dom = False

                st.write("")
                if st.button("➡️ Avançar para Próxima Fase (DOMINÓ)", type="primary", use_container_width=True, key="btn_avancar_domino"):
                    if not todos_ok_dom or len(vencedores_dom) != len(lista_mesas_normalizada):
                        st.error("⚠️ Selecione o vencedor de **todas** as mesas antes de avançar.")
                    else:
                        confs_convertidos = [{"j1": m["participantes"][0], "j2": m["participantes"][1] if len(m["participantes"]) > 1 else "BYE (Passa direto)", "vencedor": m.get("vencedor")} for m in lista_mesas_normalizada]
                        processar_avanco_fase(turma_dom_sel, "Dominó", fase_dom_atual, confs_convertidos, vencedores_dom, professor_responsavel)
                        st.toast("⚡ Avanço de Dominó realizado!", icon="🚀")
                        st.rerun()

# ==========================================
# ABA 4: HISTÓRICO
# ==========================================
with tab_historico:
    st.markdown("## 🏆 **HISTÓRICO DE CAMPEÕES & PÓDIO**")
    historico = carregar_historico()

    if not historico:
        st.info("Nenhum pódio registrado até o momento.")
    else:
        col_pdf1, col_pdf2 = st.columns([2, 2])
        with col_pdf1:
            pdf_buffer = gerar_pdf_relatorio_completo(historico, nome_torneio)
            st.download_button(
                label="📥 Baixar Relatório em PDF",
                data=pdf_buffer,
                file_name="relatorio_campeoes.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col_pdf2:
            if st.button("🗑️ Limpar Todo o Histórico", use_container_width=True):
                resetar_historico()
                st.rerun()

        st.divider()
        for h in historico:
            mod = h.get("modalidade", "").upper()
            turma = h.get("turma", "")
            resp = h.get("responsavel", "Não informado")
            podio = h.get("podio", {})
            st.markdown(f"""
                <div class="dupla-card">
                    <h3>🏆 {mod} - Turma: {turma}</h3>
                    <p>👨‍🏫 <b>Professor(a):</b> {resp}</p>
                    <p>🥇 <b>1º Lugar (Ouro):</b> {podio.get('1º', 'A definir')}</p>
                    <p>🥈 <b>2º Lugar (Prata):</b> {podio.get('2º', 'A definir')}</p>
                    <p>🥉 <b>3º Lugar (Bronze):</b> {podio.get('3º', 'A definir')}</p>
                </div>
            """, unsafe_allow_html=True)

# ==========================================
# ABA 5: ALUNOS
# ==========================================
with tab_alunos:
    st.markdown("## 👥 **GESTÃO DE ALUNOS**")
    turmas = carregar_turmas()
    alunos = carregar_alunos()

    if not turmas:
        st.info("Cadastre turmas primeiro na barra lateral.")
    else:
        st.subheader("📝 Cadastrar Novo Aluno")
        col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
        with col_c1:
            novo_nome_aluno = st.text_input("Nome do Aluno:", key="input_novo_aluno_aba")
        with col_c2:
            turma_aluno_aba = st.selectbox("Turma:", turmas, key="select_turma_aluno_aba")
        with col_c3:
            st.write("")
            st.write("")
            if st.button("➕ Cadastrar", use_container_width=True):
                if novo_nome_aluno.strip():
                    cadastrar_aluno(novo_nome_aluno.strip(), turma_aluno_aba)
                    st.toast(f"✅ {novo_nome_aluno} cadastrado!", icon="🎉")
                    st.rerun()
                else:
                    st.warning("Digite o nome.")

        st.divider()
        st.subheader("📋 Lista de Alunos por Turma (Com Opção de Exclusão/Alteração)")
        tab_turmas = st.tabs(turmas)
        for idx_t, t_nome in enumerate(turmas):
            with tab_turmas[idx_t]:
                alunos_turma = [a for a in alunos if a["turma"] == t_nome]
                if not alunos_turma:
                    st.info("Nenhum aluno cadastrado nesta turma.")
                else:
                    for idx_a, a in enumerate(alunos_turma):
                        col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
                        with col_a1:
                            st.markdown(f"👤 **{a['nome']}**")
                        with col_a2:
                            chave_selectbox = f"transf_{idx_t}_{idx_a}_{a['nome']}"
                            nova_turma_transf = st.selectbox("Mudar Turma", turmas, index=turmas.index(a['turma']), key=chave_selectbox)
                            if nova_turma_transf != a['turma']:
                                atualizar_aluno_turma(a['nome'], t_nome, a['nome'], nova_turma_transf)
                                st.rerun()
                        with col_a3:
                            chave_botao = f"del_{idx_t}_{idx_a}_{a['nome']}"
                            if st.button("🗑️ Excluir", key=chave_botao, use_container_width=True):
                                deletar_aluno(a['nome'], t_nome)
                                st.toast(f"🗑️ Aluno {a['nome']} removido.", icon="⚠️")
                                st.rerun()
