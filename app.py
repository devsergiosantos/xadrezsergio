import random
import time
import io
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

# Estilo CSS customizado para destacar os menus (Xadrez, Dama, Dominó), touchscreen e relógio
st.markdown("""
    <style>
        /* Destaque Especial nos Títulos das Abas de Menu */
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
        div.stButton > button.btn-alerta-minuto {
            background-color: #ff2b2b !important;
            color: white !important;
            height: 2.2em !important;
            font-size: 13px !important;
            border: none !important;
            box-shadow: 0 0 10px rgba(255, 43, 43, 0.6);
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.03); }
            100% { transform: scale(1); }
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
    st.info("Crie um arquivo chamado `requirements.txt` no seu repositório com:\n\n```text\nstreamlit\npymongo\ndnspython\nstreamlit-autorefresh\nreportlab\n```")
    st.stop()

if not AUTOREFRESH_INSTALADO:
    st.error("⚠ O pacote `streamlit-autorefresh` não está instalado no ambiente!")
    st.info("Adicione `streamlit-autorefresh` ao seu arquivo `requirements.txt`.")
    st.stop()

if not REPORTLAB_INSTALADO:
    st.error("⚠ O pacote `reportlab` não está instalado no ambiente!")
    st.info("Adicione `reportlab` ao seu arquivo `requirements.txt` para gerar arquivos PDF.")
    st.stop()

# --- CONEXÃO COM O MONGODB ---
MONGO_URI = st.secrets.get("MONGO_URI", "")

@st.cache_resource
def get_database():
    if not MONGO_URI:
        return None
    client = MongoClient(MONGO_URI)
    return client["torneio_escolar"]

db = None
if MONGO_URI:
    try:
        db = get_database()
        colecao_alunos = db["alunos"]
        colecao_turmas = db["turmas"]
        colecao_confrontos = db["confrontos"]
        colecao_historico = db["historico_podio"]
    except Exception as e:
        st.error(f"Erro ao conectar ao MongoDB: {e}")

if db is None:
    st.warning("⚠️ **Conexão com o MongoDB não configurada.**")
    st.info("Adicione a variável `MONGO_URI` em **Settings > Secrets** no Streamlit Cloud para salvar os dados na nuvem.")
    st.stop()

# --- FUNÇÕES DO BANCO DE DADOS ---
def carregar_turmas():
    turmas_docs = list(colecao_turmas.find({}, {"_id": 0}))
    if not turmas_docs:
        # Turmas padrão iniciais caso o banco esteja vazio
        padroes = ["1º Ano A", "1º Ano B", "2º Ano A", "3º Ano A", "4º Ano A", "5º Ano A", "6º Ano A", "7º Ano A", "8º Ano A", "9º Ano A"]
        for t in padroes:
            colecao_turmas.update_one({"nome": t}, {"$set": {"nome": t}}, upsert=True)
        return padroes
    return [t["nome"] for t in turmas_docs]

def cadastrar_turma(nome_turma):
    if not colecao_turmas.find_one({"nome": nome_turma}):
        colecao_turmas.insert_one({"nome": nome_turma})
        return True
    return False

def deletar_turma(nome_turma):
    colecao_turmas.delete_one({"nome": nome_turma})

def carregar_alunos():
    return list(colecao_alunos.find({}, {"_id": 0}))

def cadastrar_aluno(nome, turma):
    colecao_alunos.insert_one({"nome": nome, "turma": turma})

def carregar_confrontos(turma, modalidade, fase):
    doc = colecao_confrontos.find_one({"turma": turma, "modalidade": modalidade, "fase": fase})
    return doc["confrontos"] if doc else []

def salvar_confrontos(turma, modalidade, fase, lista_confrontos):
    colecao_confrontos.update_one(
        {"turma": turma, "modalidade": modalidade, "fase": fase},
        {"$set": {"turma": turma, "modalidade": modalidade, "fase": fase, "confrontos": lista_confrontos}},
        upsert=True
    )

def resetar_torneio_turma(turma, modalidade):
    colecao_confrontos.delete_many({"turma": turma, "modalidade": modalidade})

def salvar_podio(turma, modalidade, podio_dict):
    podio_limpo = {
        "1º": podio_dict.get("1º", "A definir"),
        "2º": podio_dict.get("2º", "A definir"),
        "3º": podio_dict.get("3º", "A definir")
    }
    colecao_historico.update_one(
        {"turma": turma, "modalidade": modalidade},
        {"$set": {"turma": turma, "modalidade": modalidade, "podio": podio_limpo}},
        upsert=True
    )

def carregar_historico():
    return list(colecao_historico.find({}, {"_id": 0}))

def resetar_historico():
    colecao_historico.delete_many({})

# --- FUNÇÃO PARA GERAR PDF DO HISTÓRICO ---
def gerar_pdf_historico(historico_dados, nome_torneio):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=1,
        spaceAfter=20,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    story.append(Paragraph(f"<b>{nome_torneio.upper()}</b>", title_style))
    story.append(Paragraph("<b>Relatório Oficial de Campeões & Pódio</b>", ParagraphStyle('Sub', parent=styles['Normal'], alignment=1, fontSize=12, spaceAfter=20)))
    story.append(Spacer(1, 10))

    tabela_dados = [["Modalidade", "Turma", "1º Lugar (Ouro)", "2º Lugar (Prata)", "3º Lugar (Bronze)"]]

    for h in historico_dados:
        mod = h.get("modalidade", "Jogo").upper()
        turma = h.get("turma", "Geral")
        podio = h.get("podio", {})
        
        p1 = podio.get("1º", "A definir")
        p2 = podio.get("2º", "A definir")
        p3 = podio.get("3º", "A definir")
        
        tabela_dados.append([mod, turma, p1, p2, p3])

    t = Table(tabela_dados, colWidths=[90, 80, 125, 125, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
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

# Lógica de contagem em tempo real rodando em background com auto-refresh
if st.session_state.timer_running:
    agora = time.time()
    passado = int(agora - st.session_state.last_tick)
    if passado > 0:
        st.session_state.seconds_remaining = max(0, st.session_state.seconds_remaining - passado)
        st.session_state.last_tick = agora
        if st.session_state.seconds_remaining == 0:
            st.session_state.timer_running = False

    st_autorefresh(interval=1000, key="relogio_counter")

# --- BARRA LATERAL (MENU DE CADASTRO E GERENCIAMENTO) ---
with st.sidebar:
    st.header("⚙️ Configurações & Cadastro")
    nome_torneio = st.text_input("Nome do Torneio:", "Torneio de Jogos Escolares")
    
    st.divider()
    st.subheader("🏫 Gerenciar Turmas")
    nova_turma_input = st.text_input("Nome da Turma (Ex: 1º Ano A):", key="cad_turma_nova")
    if st.button("➕ Adicionar Turma", use_container_width=True):
        if nova_turma_input.strip():
            sucesso = cadastrar_turma(nova_turma_input.strip())
            if sucesso:
                st.toast(f"✅ Turma {nova_turma_input.strip()} cadastrada!", icon="🎉")
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
                st.toast(f"🗑️ Turma {turma_a_remover} removida.", icon="⚠️")
                st.rerun()

    st.divider()
    st.subheader("📝 Cadastrar Aluno")
    novo_nome = st.text_input("Nome do Aluno:", key="cad_nome")
    turma_aluno_sel = st.selectbox("Turma do Aluno:", turmas_atuais if turmas_atuais else ["Nenhuma turma"], key="cad_turma_aluno")
    
    if st.button("➕ Cadastrar Aluno", use_container_width=True):
        if novo_nome.strip() and turmas_atuais:
            cadastrar_aluno(novo_nome.strip(), turma_aluno_sel)
            st.toast(f"✅ {novo_nome.strip()} cadastrado com sucesso!", icon="🎉")
            st.rerun()
        else:
            st.warning("Preencha o nome e cadastre ao menos uma turma.")

# --- COMPONENTE DO RELÓGIO FIXO NA PRIMEIRA PÁGINA (CANTO ESQUERDO) ---
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

        if 0 < st.session_state.seconds_remaining <= 60:
            st.button("⚠️ RESTA 1 MINUTO!", key="btn_alerta_um_minuto", use_container_width=True, type="primary")

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

        if st.session_state.seconds_remaining == 0:
            st.error("🚨 **TEMPO ESGOTADO!**")

# --- INTERFACE PRINCIPAL EM ABAS ---
st.title(f"♟️ {nome_torneio}")

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
            st.info("👋 Nenhuma turma cadastrada. Use o menu lateral (⚙️) para adicionar turmas e alunos.")
        else:
            turma_selecionada = st.selectbox("🎯 Selecione a Turma para Xadrez:", turmas_disponiveis, key="turma_xadrez")
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
                    st.error("É necessário ter pelo menos 2 alunos cadastrados nesta turma.")
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
                    st.success(f"Fase 1 de XADREZ sorteada para o {turma_selecionada}!")
                    st.rerun()

            if btn_limpar:
                resetar_torneio_turma(turma_selecionada, "Xadrez")
                st.toast("Torneio de Xadrez zerado para esta turma.", icon="🧹")
                st.rerun()

            fases_registradas = list(colecao_confrontos.find({"turma": turma_selecionada, "modalidade": "Xadrez"}).sort("fase", -1))
            fase_atual = fases_registradas[0]["fase"] if fases_registradas else 1
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

                    with st.form(key=f"form_fase_xadrez_{fase_atual}_{turma_selecionada}"):
                        for idx, c in enumerate(confrontos_fase):
                            st.markdown(f"""<div class="dupla-card"><b>Partida {idx + 1} (XADREZ)</b></div>""", unsafe_allow_html=True)
                            j1, j2 = c["j1"], c["j2"]

                            if j2 == "BYE (Passa direto)":
                                st.info(f"⚪ **{j1}** avança automaticamente.")
                                vencedores.append(j1)
                            else:
                                opcoes = ["Selecione...", j1, j2]
                                index_padrao = opcoes.index(c["vencedor"]) if c.get("vencedor") in opcoes else 0

                                escolha = st.radio(
                                    f"Vencedor da Partida {idx + 1} (Valendo {pontos_por_vitoria} pts):",
                                    opcoes,
                                    index=index_padrao,
                                    key=f"px_{fase_atual}_{idx}"
                                )
                                if escolha != "Selecione...":
                                    vencedores.append(escolha)
                                else:
                                    todos_selecionados = False

                        btn_avancar = st.form_submit_button("Avançar para Próxima Fase ➡️", use_container_width=True)

                        if btn_avancar:
                            if not todos_selecionados:
                                st.error("Selecione o vencedor de todas as partidas antes de avançar.")
                            else:
                                salvar_confrontos(turma_selecionada, "Xadrez", fase_atual, [
                                    {**c, "vencedor": vencedores[i]} for i, c in enumerate(confrontos_fase)
                                ])

                                if len(vencedores) == 1:
                                    primeiro = vencedores[0]
                                    
                                    partida_final = confrontos_fase[0]
                                    segundo = partida_final["j2"] if partida_final["j1"] == primeiro else partida_final["j1"]
                                    if segundo == "BYE (Passa direto)":
                                        segundo = "Sem vice-campeão"

                                    terceiro = "A definir"
                                    if fase_atual > 1:
                                        fase_anterior = carregar_confrontos(turma_selecionada, "Xadrez", fase_atual - 1)
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

                                    salvar_podio(turma_selecionada, "Xadrez", {"1º": primeiro, "2º": segundo, "3º": terceiro})
                                    salvar_confrontos(turma_selecionada, "Xadrez", fase_atual + 1, [{"j1": primeiro, "j2": None, "vencedor": primeiro}])
                                    st.rerun()
                                else:
                                    novos_confrontos = []
                                    random.shuffle(vencedores)
                                    for i in range(0, len(vencedores), 2):
                                        if i + 1 < len(vencedores):
                                            novos_confrontos.append({"j1": vencedores[i], "j2": vencedores[i+1], "vencedor": None})
                                        else:
                                            novos_confrontos.append({"j1": vencedores[i], "j2": "BYE (Passa direto)", "vencedor": vencedores[i]})

                                    salvar_confrontos(turma_selecionada, "Xadrez", fase_atual + 1, novos_confrontos)
                                    st.rerun()

# ==========================================
# ABA 2: DAMA
# ==========================================
with tab_dama:
    st.markdown("## 👑 **MODALIDADE: DAMA (2 JOGADORES POR PARTIDA)**")
    alunos_db = carregar_alunos()
    turmas_dama = carregar_turmas()

    if not turmas_dama:
        st.info("👋 Cadastre turmas e alunos na barra lateral para iniciar.")
    else:
        turma_dama_sel = st.selectbox("🎯 Selecione a Turma para DAMA:", turmas_dama, key="turma_dama")
        pts_dama = st.radio("🏅 Pontuação por vitória:", [2, 10], horizontal=True, key="pts_dama")
        alunos_dama_filtrados = [a["nome"] for a in alunos_db if a["turma"] == turma_dama_sel]

        col_sd1, col_sd2 = st.columns(2)
        with col_sd1:
            btn_sort_dama = st.button("🎲 Sortear Partidas de DAMA", type="primary", use_container_width=True)
        with col_sd2:
            btn_limp_dama = st.button("🗑️ Reiniciar DAMA", use_container_width=True)

        if btn_sort_dama:
            if len(alunos_dama_filtrados) < 2:
                st.error("São necessários pelo menos 2 alunos nesta turma.")
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
                st.success("Sorteio de DAMA realizado com sucesso!")
                st.rerun()

        if btn_limp_dama:
            resetar_torneio_turma(turma_dama_sel, "Dama")
            st.toast("Torneio de DAMA reiniciado.", icon="🧹")
            st.rerun()

        fases_dama = list(colecao_confrontos.find({"turma": turma_dama_sel, "modalidade": "Dama"}).sort("fase", -1))
        fase_dama_atual = fases_dama[0]["fase"] if fases_dama else 1
        confs_dama = carregar_confrontos(turma_dama_sel, "Dama", fase_dama_atual)

        if confs_dama:
            st.markdown(f"#### Fase {fase_dama_atual} - DAMA ({turma_dama_sel})")

            if len(confs_dama) == 1 and confs_dama[0].get("j2") is None:
                campeao_dama = confs_dama[0]["j1"]
                st.success(f"🏆 **CAMPEÃO DE DAMA DO {turma_dama_sel.upper()}: {campeao_dama}** 🏆")
            else:
                vencedores_dama = []
                todos_ok = True

                with st.form(key=f"form_dama_{fase_dama_atual}_{turma_dama_sel}"):
                    for idx, c in enumerate(confs_dama):
                        st.markdown(f"""<div class="dupla-card"><b>Partida DAMA {idx + 1}</b></div>""", unsafe_allow_html=True)
                        j1, j2 = c["j1"], c["j2"]
                        if j2 == "BYE (Passa direto)":
                            st.info(f"⚪ **{j1}** avança automaticamente.")
                            vencedores_dama.append(j1)
                        else:
                            opcoes = ["Selecione...", j1, j2]
                            index_padrao = opcoes.index(c["vencedor"]) if c.get("vencedor") in opcoes else 0
                            escolha = st.radio(f"Vencedor da Partida {idx + 1} ({pts_dama} pts):", opcoes, index=index_padrao, key=f"pd_{idx}")
                            if escolha != "Selecione...":
                                vencedores_dama.append(escolha)
                            else:
                                todos_ok = False

                    if st.form_submit_button("Avançar DAMA ➡️", use_container_width=True):
                        if not todos_ok:
                            st.error("Selecione todos os vencedores.")
                        else:
                            salvar_confrontos(turma_dama_sel, "Dama", fase_dama_atual, [{**c, "vencedor": vencedores_dama[i]} for i, c in enumerate(confs_dama)])
                            if len(vencedores_dama) == 1:
                                primeiro = vencedores_dama[0]
                                
                                partida_final = confs_dama[0]
                                segundo = partida_final["j2"] if partida_final["j1"] == primeiro else partida_final["j1"]
                                if segundo == "BYE (Passa direto)":
                                    segundo = "Sem vice-campeão"

                                terceiro = "A definir"
                                if fase_dama_atual > 1:
                                    fase_anterior = carregar_confrontos(turma_dama_sel, "Dama", fase_dama_atual - 1)
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

                                salvar_confrontos(turma_dama_sel, "Dama", fase_dama_atual + 1, [{"j1": primeiro, "j2": None, "vencedor": primeiro}])
                                salvar_podio(turma_dama_sel, "Dama", {"1º": primeiro, "2º": segundo, "3º": terceiro})
                                st.rerun()
                            else:
                                novos = []
                                random.shuffle(vencedores_dama)
                                for i in range(0, len(vencedores_dama), 2):
                                    if i + 1 < len(vencedores_dama):
                                        novos.append({"j1": vencedores_dama[i], "j2": vencedores_dama[i+1], "vencedor": None})
                                    else:
                                        novos.append({"j1": vencedores_dama[i], "j2": "BYE (Passa direto)", "vencedor": vencedores_dama[i]})
                                salvar_confrontos(turma_dama_sel, "Dama", fase_dama_atual + 1, novos)
                                st.rerun()

# ==========================================
# ABA 3: DOMINÓ
# ==========================================
with tab_domino:
    st.markdown("## 🀄 **MODALIDADE: DOMINÓ (2, 3 OU 4 JOGADORES)**")
    alunos_db = carregar_alunos()
    turmas_domino = carregar_turmas()

    if not turmas_domino:
        st.info("👋 Cadastre turmas e alunos na barra lateral para iniciar.")
    else:
        turma_dom_sel = st.selectbox("🎯 Selecione a Turma para DOMINÓ:", turmas_domino, key="turma_dom")
        tamanho_mesa = st.selectbox("👥 Alunos por Mesa/Partida:", [2, 3, 4], key="tam_mesa_dom")
        pts_dom = st.radio("🏅 Pontuação por vitória:", [2, 10], horizontal=True, key="pts_dom")
        
        alunos_dom_filtrados = [a["nome"] for a in alunos_db if a["turma"] == turma_dom_sel]

        col_dom1, col_dom2 = st.columns(2)
        with col_dom1:
            btn_sort_dom = st.button("🎲 Sortear Mesas de DOMINÓ", type="primary", use_container_width=True)
        with col_dom2:
            btn_limp_dom = st.button("🗑️ Reiniciar DOMINÓ", use_container_width=True)

        if btn_sort_dom:
            if len(alunos_dom_filtrados) < tamanho_mesa:
                st.error(f"São necessários pelo menos {tamanho_mesa} alunos para esta configuração.")
            else:
                resetar_torneio_turma(turma_dom_sel, "Dominó")
                jogadores = alunos_dom_filtrados.copy()
                random.shuffle(jogadores)
                
                mesas = []
                for i in range(0, len(jogadores), tamanho_mesa):
                    grupo = jogadores[i:i + tamanho_mesa]
                    mesas.append({"jogadores": grupo, "vencedor": None})
                
                salvar_confrontos(turma_dom_sel, "Dominó", 1, mesas)
                st.success("Sorteio de DOMINÓ realizado com sucesso!")
                st.rerun()

        if btn_limp_dom:
            resetar_torneio_turma(turma_dom_sel, "Dominó")
            st.toast("Torneio de DOMINÓ reiniciado.", icon="🧹")
            st.rerun()

        fases_dom = list(colecao_confrontos.find({"turma": turma_dom_sel, "modalidade": "Dominó"}).sort("fase", -1))
        fase_dom_atual = fases_dom[0]["fase"] if fases_dom else 1
        confs_dom = carregar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual)

        if confs_dom:
            st.markdown(f"#### Fase {fase_dom_atual} - DOMINÓ ({turma_dom_sel})")

            if len(confs_dom) == 1 and len(confs_dom[0].get("jogadores", [])) == 1:
                campeao_domino = confs_dom[0]["jogadores"][0]
                st.success(f"🏆 **GRANDE CAMPEÃO DE DOMINÓ DO {turma_dom_sel.upper()}: {campeao_domino}** 🏆")
            else:
                vencedores_dom = []
                todos_ok_dom = True

                with st.form(key=f"form_dom_{fase_dom_atual}_{turma_dom_sel}"):
                    for idx, m in enumerate(confs_dom):
                        st.markdown(f"""<div class="dupla-card"><b>Mesa {idx + 1} (DOMINÓ)</b> (Participantes: {', '.join(m['jogadores'])})</div>""", unsafe_allow_html=True)
                        opcoes = ["Selecione o vencedor..."] + m["jogadores"]
                        index_padrao = opcoes.index(m["vencedor"]) if m.get("vencedor") in opcoes else 0
                        
                        escolha = st.selectbox(f"Vencedor da Mesa {idx + 1} ({pts_dom} pts):", opcoes, index=index_padrao, key=f"md_{idx}")
                        if escolha != "Selecione o vencedor...":
                            vencedores_dom.append(escolha)
                        else:
                            todos_ok_dom = False

                    if st.form_submit_button("Avançar DOMINÓ ➡️", use_container_width=True):
                        if not todos_ok_dom:
                            st.error("Selecione o vencedor de todas as mesas.")
                        else:
                            salvar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual, [{**m, "vencedor": vencedores_dom[i]} for i, m in enumerate(confs_dom)])
                            if len(vencedores_dom) == 1:
                                primeiro = vencedores_dom[0]
                                mesa_final = confs_dom[0]["jogadores"]
                                demais_finalistas = [p for p in mesa_final if p != primeiro]

                                segundo = demais_finalistas[0] if len(demais_finalistas) > 0 else "Sem vice-campeão"
                                terceiro = demais_finalistas[1] if len(demais_finalistas) > 1 else "A definir"

                                salvar_podio(turma_dom_sel, "Dominó", {"1º": primeiro, "2º": segundo, "3º": terceiro})
                                salvar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual + 1, [{"jogadores": [primeiro], "vencedor": primeiro}])
                                st.rerun()
                            else:
                                novos_mesas = []
                                random.shuffle(vencedores_dom)
                                for i in range(0, len(vencedores_dom), tamanho_mesa):
                                    grupo = vencedores_dom[i:i + tamanho_mesa]
                                    novos_mesas.append({"jogadores": grupo, "vencedor": None})
                                salvar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual + 1, novos_mesas)
                                st.rerun()

# ==========================================
# ABA 4: HISTÓRICO E PÓDIO
# ==========================================
with tab_historico:
    st.markdown("## 🏆 **HISTÓRICO GERAL & PÓDIO**")
    historico_dados = carregar_historico()

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        if historico_dados:
            pdf_buffer = gerar_pdf_historico(historico_dados, nome_torneio)
            st.download_button(
                label="📥 Baixar Relatório em PDF",
                data=pdf_buffer,
                file_name="relatorio_campeoes_torneio.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    with col_h2:
        if historico_dados:
            if st.button("🗑️ Limpar Histórico Completo", use_container_width=True):
                resetar_historico()
                st.toast("Histórico limpo com sucesso!", icon="🧹")
                st.rerun()

    st.divider()

    if not historico_dados:
        st.info("Nenhum pódio registrado ainda. Conclua os torneios nas turmas e modalidades para preencher o histórico.")
    else:
        for h in historico_dados:
            mod = h.get("modalidade", "Modalidade")
            turma = h.get("turma", "Turma")
            podio = h.get("podio", {})

            st.markdown(f"""
                <div class="dupla-card">
                    <h3>🎮 {mod} — Turma: {turma}</h3>
                    <p>🥇 <b>1º Lugar (Ouro):</b> {podio.get('1º', 'A definir')}</p>
                    <p>🥈 <b>2º Lugar (Prata):</b> {podio.get('2º', 'A definir')}</p>
                    <p>🥉 <b>3º Lugar (Bronze):</b> {podio.get('3º', 'A definir')}</p>
                </div>
            """, unsafe_allow_html=True)

# ==========================================
# ABA 5: ALUNOS CADASTRADOS
# ==========================================
with tab_alunos:
    st.markdown("## 👥 **ALUNOS CADASTRADOS**")
    alunos_db = carregar_alunos()
    
    if not alunos_db:
        st.info("Nenhum aluno cadastrado no momento.")
    else:
        turmas_cadastradas = sorted(list(set(a["turma"] for a in alunos_db)))
        for t in turmas_cadastradas:
            st.markdown(f"### Turma: {t}")
            participantes = [a["nome"] for a in alunos_db if a["turma"] == t]
            for idx, aluno in enumerate(participantes, 1):
                st.write(f"{idx}. {aluno}")
            st.divider()
