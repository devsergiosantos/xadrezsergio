import random
import time
import streamlit as st

# --- TRATAMENTO DE IMPORTAÇÃO ---
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
    st.info("Crie um arquivo chamado `requirements.txt` no seu repositório com:\n\n```text\nstreamlit\npymongo\ndnspython\nstreamlit-autorefresh\n```")
    st.stop()

if not AUTOREFRESH_INSTALADO:
    st.error("⚠ O pacote `streamlit-autorefresh` não está instalado no ambiente!")
    st.info("Adicione `streamlit-autorefresh` ao seu arquivo `requirements.txt`.")
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
        colecao_confrontos = db["confrontos"]
        colecao_historico = db["historico_podio"]
    except Exception as e:
        st.error(f"Erro ao conectar ao MongoDB: {e}")

if db is None:
    st.warning("⚠️ **Conexão com o MongoDB não configurada.**")
    st.info("Adicione a variável `MONGO_URI` em **Settings > Secrets** no Streamlit Cloud para salvar os dados na nuvem.")
    st.stop()

# --- FUNÇÕES DO BANCO DE DADOS ---
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
    colecao_historico.update_one(
        {"turma": turma, "modalidade": modalidade},
        {"$set": {"podio": podio_dict}},
        upsert=True
    )

def carregar_historico():
    return list(colecao_historico.find({}, {"_id": 0}))

def resetar_historico():
    colecao_historico.delete_many({})

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

# --- BARRA LATERAL (MENU DE CADASTRO) ---
with st.sidebar:
    st.header("⚙️ Configurações & Cadastro")
    nome_torneio = st.text_input("Nome do Torneio:", "Torneio de Jogos Escolares")
    
    st.divider()
    st.subheader("📝 Cadastrar Aluno")
    novo_nome = st.text_input("Nome do Aluno:", key="cad_nome")
    nova_turma = st.selectbox(
        "Turma:",
        ["1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano"],
        key="cad_turma"
    )
    if st.button("➕ Cadastrar", use_container_width=True):
        if novo_nome.strip():
            cadastrar_aluno(novo_nome.strip(), nova_turma)
            st.success(f"{novo_nome} cadastrado com sucesso!")
            st.rerun()
        else:
            st.warning("Digite o nome do aluno.")

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

        # Botão vermelho pequeno exibido quando resta 1 minuto ou menos (e o tempo ainda não zerou)
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

# --- INTERFACE PRINCIPAL EM ABAS (NOMES DOS MENUS DESTACADOS) ---
st.title(f"♟️ {nome_torneio}")

tab_xadrez, tab_dama, tab_domino, tab_historico, tab_alunos = st.tabs([
    "⚔️ XADREZ", "👑 DAMA", "🀄 DOMINÓ", "🏆 HISTÓRICO", "👥 ALUNOS"
])

# ==========================================
# ABA 1: XADREZ (COM EMPARELHAMENTO E PONTUAÇÃO)
# ==========================================
with tab_xadrez:
    col_relogio_esq, col_conteudo_dir = st.columns([1, 3])
    
    with col_relogio_esq:
        renderizar_relogio_lateral()
        
    with col_conteudo_dir:
        st.markdown("## ⚔️ **MODALIDADE: XADREZ**")
        alunos_db = carregar_alunos()
        turmas_disponiveis = sorted(list(set(a["turma"] for a in alunos_db)))

        if not turmas_disponiveis:
            st.info("👋 Nenhum aluno cadastrado. Use o menu lateral (⚙️) para cadastrar os alunos.")
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
                    salvar_podio(turma_selecionada, "Xadrez", {"1º": campeao, "2º": "Finalista", "3º": "Semifinalista"})
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
                                    salvar_confrontos(turma_selecionada, "Xadrez", fase_atual + 1, [{"j1": vencedores[0], "j2": None, "vencedor": vencedores[0]}])
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
# ABA 2: DAMA (2 ALUNOS POR PARTIDA)
# ==========================================
with tab_dama:
    st.markdown("## 👑 **MODALIDADE: DAMA (2 JOGADORES POR PARTIDA)**")
    alunos_db = carregar_alunos()
    turmas_dama = sorted(list(set(a["turma"] for a in alunos_db)))

    if not turmas_dama:
        st.info("👋 Cadastre alunos na barra lateral para iniciar.")
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
                            salvar_confrontos(turma_dama_sel, "Dama", fase_dama_atual + 1, [{"j1": vencedores_dama[0], "j2": None, "vencedor": vencedores_dama[0]}])
                            salvar_podio(turma_dama_sel, "Dama", {"1º": vencedores_dama[0], "2º": "Finalista", "3º": "Semifinalista"})
                            st.success(f"🏆 Campeão de DAMA: {vencedores_dama[0]}!")
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
# ABA 3: DOMINÓ (2, 3 OU 4 ALUNOS POR PARTIDA)
# ==========================================
with tab_domino:
    st.markdown("## 🀄 **MODALIDADE: DOMINÓ (2, 3 OU 4 JOGADORES)**")
    alunos_db = carregar_alunos()
    turmas_domino = sorted(list(set(a["turma"] for a in alunos_db)))

    if not turmas_domino:
        st.info("👋 Cadastre alunos na barra lateral para iniciar.")
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
                            salvar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual + 1, [{"jogadores": [vencedores_dom[0]], "vencedor": vencedores_dom[0]}])
                            salvar_podio(turma_dom_sel, "Dominó", {"1º": vencedores_dom[0], "2º": "Finalista", "3º": "Semifinalista"})
                            st.success(f"🏆 Grande Campeão de DOMINÓ: {vencedores_dom[0]}!")
                            st.rerun()
                        else:
                            novas_mesas = []
                            random.shuffle(vencedores_dom)
                            for i in range(0, len(vencedores_dom), tamanho_mesa):
                                grupo = vencedores_dom[i:i + tamanho_mesa]
                                novas_mesas.append({"jogadores": grupo, "vencedor": None})
                            salvar_confrontos(turma_dom_sel, "Dominó", fase_dom_atual + 1, novas_mesas)
                            st.rerun()

# ==========================================
# ABA 4: HISTÓRICO DE VENCEDORES (1º, 2º e 3º LUGAR)
# ==========================================
with tab_historico:
    col_hist_title, col_hist_btn = st.columns([3, 1])
    
    with col_hist_title:
        st.subheader("🏆 HISTÓRICO GERAL DE VENCEDORES")
    
    with col_hist_btn:
        if st.button("🗑️ Zerar Histórico", use_container_width=True):
            st.session_state["confirmar_zerar_historico"] = True

    # Diálogo de confirmação para evitar exclusão acidental
    if st.session_state.get("confirmar_zerar_historico", False):
        st.warning("⚠️ Tem certeza de que deseja apagar **todo** o histórico de campeões?")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("✅ Sim, apagar tudo", type="primary", use_container_width=True):
                resetar_historico()
                st.session_state["confirmar_zerar_historico"] = False
                st.toast("Histórico zerado com sucesso!", icon="🧹")
                st.rerun()
        with col_c2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state["confirmar_zerar_historico"] = False
                st.rerun()

    st.divider()

    historico_db = carregar_historico()

    if historico_db:
        for item in historico_db:
            turma = item.get("turma", "Geral")
            modalidade = item.get("modalidade", "Jogo")
            podio = item.get("podio", {})
            
            st.markdown(f"""
                <div class="dupla-card">
                    <h4>🏅 {modalidade.upper()} - Turma: {turma}</h4>
                    <p>🥇 <b>1º Lugar:</b> {podio.get('1º', 'A definir')}</p>
                    <p>🥈 <b>2º Lugar:</b> {podio.get('2º', 'A definir')}</p>
                    <p>🥉 <b>3º Lugar:</b> {podio.get('3º', 'A definir')}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum pódio registrado ainda. Conclua os torneios para preencher o histórico.")

# ==========================================
# ABA 5: LISTA DE ALUNOS
# ==========================================
with tab_alunos:
    st.subheader("📋 LISTA GERAL DE INSCRITOS")
    alunos_db = carregar_alunos()
    
    if alunos_db:
        st.dataframe(alunos_db, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum aluno cadastrado ainda.")
