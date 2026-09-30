import random
import time
import streamlit as st

# --- TRATAMENTO DE IMPORTAÇÃO ---
try:
    from pymongo import MongoClient
    PYMONGO_INSTALADO = True
except ImportError:
    PYMONGO_INSTALADO = False

# --- CONFIGURAÇÃO DE PÁGINA (RESPONSIVO PARA MOBILE, TABLET E PC) ---
st.set_page_config(
    page_title="Torneio de Xadrez Escolar",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo CSS customizado para touchscreen
st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            height: 3em;
            font-size: 16px !important;
            font-weight: bold;
            border-radius: 8px;
        }
        div[role="radiogroup"] label {
            padding: 10px;
            background-color: #f0f2f6;
            border-radius: 8px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
        }
        @media (prefers-color-scheme: dark) {
            div[role="radiogroup"] label {
                background-color: #262730;
            }
        }
    </style>
""", unsafe_allow_html=True)

# Verificação inicial do pacote pymongo
if not PYMONGO_INSTALADO:
    st.error("⚠ O pacote `pymongo` não está instalado no ambiente!")
    st.info("Crie um arquivo chamado `requirements.txt` no seu repositório com o conteúdo:\n\n```text\nstreamlit\npymongo\ndnspython\n```")
    st.stop()

# --- CONEXÃO COM O MONGODB ---
MONGO_URI = st.secrets.get("MONGO_URI", "")

@st.cache_resource
def get_database():
    if not MONGO_URI:
        return None
    # CORREÇÃO: Remoção das aspas em MONGO_URI
    client = MongoClient(MONGO_URI)
    return client["xadrez_torneio"]

db = None
if MONGO_URI:
    try:
        db = get_database()
        colecao_alunos = db["alunos"]
        colecao_confrontos = db["confrontos"]
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

def carregar_confrontos(turma, fase):
    doc = colecao_confrontos.find_one({"turma": turma, "fase": fase})
    return doc["confrontos"] if doc else []

def salvar_confrontos(turma, fase, lista_confrontos):
    colecao_confrontos.update_one(
        {"turma": turma, "fase": fase},
        {"$set": {"turma": turma, "fase": fase, "confrontos": lista_confrontos}},
        upsert=True
    )

def resetar_torneio_turma(turma):
    colecao_confrontos.delete_many({"turma": turma})

# --- ESTADO DO TEMPORIZADOR ---
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "seconds_remaining" not in st.session_state:
    st.session_state.seconds_remaining = 300

# --- BARRA LATERAL (MENU DE CADASTRO) ---
with st.sidebar:
    st.header("⚙️ Configurações & Cadastro")
    nome_torneio = st.text_input("Nome do Torneio:", "Torneio de Xadrez Escolar")
    
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

# --- INTERFACE PRINCIPAL EM ABAS ---
st.title(f"♟️ {nome_torneio}")

tab_partidas, tab_timer, tab_alunos = st.tabs(["⚔️ Partidas", "⏱️ Temporizador", "👥 Alunos Cadastrados"])

# ==========================================
# ABA 1: PARTIDAS E SORTEIO
# ==========================================
with tab_partidas:
    alunos_db = carregar_alunos()
    turmas_disponiveis = sorted(list(set(a["turma"] for a in alunos_db)))

    if not turmas_disponiveis:
        st.info("👋 Nenhum aluno cadastrado. Abra o menu lateral (⚙️ no canto superior esquerdo) para cadastrar os alunos.")
    else:
        turma_selecionada = st.selectbox("🎯 Selecione a Turma:", turmas_disponiveis)
        alunos_filtrados = [a["nome"] for a in alunos_db if a["turma"] == turma_selecionada]

        st.caption(f"Total de alunos na turma **{turma_selecionada}**: {len(alunos_filtrados)}")

        col_sort, col_res = st.columns(2)
        with col_sort:
            btn_iniciar = st.button("🎲 Sortear Fase 1", type="primary", use_container_width=True)
        with col_res:
            btn_limpar = st.button("🗑️ Reiniciar Turma", use_container_width=True)

        if btn_iniciar:
            if len(alunos_filtrados) < 2:
                st.error("É necessário ter pelo menos 2 alunos cadastrados nesta turma.")
            else:
                resetar_torneio_turma(turma_selecionada)
                jogadores = alunos_filtrados.copy()
                random.shuffle(jogadores)

                confrontos = []
                for i in range(0, len(jogadores), 2):
                    if i + 1 < len(jogadores):
                        confrontos.append({"j1": jogadores[i], "j2": jogadores[i+1], "vencedor": None})
                    else:
                        confrontos.append({"j1": jogadores[i], "j2": "BYE (Passa direto)", "vencedor": jogadores[i]})

                salvar_confrontos(turma_selecionada, 1, confrontos)
                st.success(f"Fase 1 sorteada para o {turma_selecionada}!")
                st.rerun()

        if btn_limpar:
            resetar_torneio_turma(turma_selecionada)
            st.toast("Torneio zerado para esta turma.", icon="🧹")
            st.rerun()

        fases_registradas = colecao_confrontos.find({"turma": turma_selecionada}).sort("fase", -1)
        fase_atual = fases_registradas[0]["fase"] if colecao_confrontos.count_documents({"turma": turma_selecionada}) > 0 else 1
        confrontos_fase = carregar_confrontos(turma_selecionada, fase_atual)

        st.divider()

        if confrontos_fase:
            st.subheader(f"🚩 Fase {fase_atual} - {turma_selecionada}")

            if len(confrontos_fase) == 1 and confrontos_fase[0]["j2"] is None:
                st.balloons()
                st.success(f"🏆 **CAMPEÃO DO {turma_selecionada.upper()}: {confrontos_fase[0]['j1']}** 🏆")
            else:
                vencedores = []
                todos_selecionados = True

                with st.form(key=f"form_fase_{fase_atual}_{turma_selecionada}"):
                    for idx, c in enumerate(confrontos_fase):
                        st.markdown(f"**Partida {idx + 1}**")
                        j1, j2 = c["j1"], c["j2"]

                        if j2 == "BYE (Passa direto)":
                            st.info(f"⚪ **{j1}** avança automaticamente.")
                            vencedores.append(j1)
                        else:
                            opcoes = ["Selecione...", j1, j2]
                            index_padrao = opcoes.index(c["vencedor"]) if c.get("vencedor") in opcoes else 0

                            escolha = st.radio(
                                f"Quem venceu?",
                                opcoes,
                                index=index_padrao,
                                key=f"p_{fase_atual}_{idx}"
                            )
                            if escolha != "Selecione...":
                                vencedores.append(escolha)
                            else:
                                todos_selecionados = False
                        st.write("---")

                    btn_avancar = st.form_submit_button("Avançar para Próxima Fase ➡️", use_container_width=True)

                    if btn_avancar:
                        if not todos_selecionados:
                            st.error("Selecione o vencedor de todas as partidas antes de avançar.")
                        else:
                            st.session_state.timer_running = False

                            salvar_confrontos(turma_selecionada, fase_atual, [
                                {**c, "vencedor": vencedores[i]} for i, c in enumerate(confrontos_fase)
                            ])

                            if len(vencedores) == 1:
                                salvar_confrontos(turma_selecionada, fase_atual + 1, [{"j1": vencedores[0], "j2": None, "vencedor": vencedores[0]}])
                                st.rerun()
                            else:
                                novos_confrontos = []
                                random.shuffle(vencedores)
                                for i in range(0, len(vencedores), 2):
                                    if i + 1 < len(vencedores):
                                        novos_confrontos.append({"j1": vencedores[i], "j2": vencedores[i+1], "vencedor": None})
                                    else:
                                        novos_confrontos.append({"j1": vencedores[i], "j2": "BYE (Passa direto)", "vencedor": vencedores[i]})

                                salvar_confrontos(turma_selecionada, fase_atual + 1, novos_confrontos)
                                st.rerun()

# ==========================================
# ABA 2: TEMPORIZADOR DE PARTIDA
# ==========================================
with tab_timer:
    st.subheader("⏱ Relógio de Rodada")
    
    minutos = st.number_input("Definir tempo (minutos):", min_value=1, max_value=60, value=5, step=1)
    
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("▶️ Iniciar", use_container_width=True):
            st.session_state.seconds_remaining = minutos * 60
            st.session_state.timer_running = True
            st.rerun()
    with col_b2:
        if st.button("⏸️ Pausar", use_container_width=True):
            st.session_state.timer_running = False
    with col_b3:
        if st.button("🔄 Resetar", use_container_width=True):
            st.session_state.timer_running = False
            st.session_state.seconds_remaining = minutos * 60
            st.rerun()

    timer_placeholder = st.empty()

    if st.session_state.timer_running:
        while st.session_state.seconds_remaining > 0 and st.session_state.timer_running:
            mins, secs = divmod(st.session_state.seconds_remaining, 60)
            timer_placeholder.markdown(
                f"<h1 style='text-align: center; font-size: 80px; color: #ff4b4b;'>{mins:02d}:{secs:02d}</h1>",
                unsafe_allow_html=True
            )
            time.sleep(1)
            st.session_state.seconds_remaining -= 1

        if st.session_state.seconds_remaining <= 0:
            st.session_state.timer_running = False
            timer_placeholder.markdown("<h1 style='text-align: center; font-size: 80px; color: red;'>00:00</h1>", unsafe_allow_html=True)
            st.error("🚨 **TEMPO ESGOTADO!** Finalize os tabuleiros.")
    else:
        mins, secs = divmod(st.session_state.seconds_remaining, 60)
        timer_placeholder.markdown(
            f"<h1 style='text-align: center; font-size: 80px;'>{mins:02d}:{secs:02d}</h1>",
            unsafe_allow_html=True
        )

# ==========================================
# ABA 3: LISTA DE ALUNOS
# ==========================================
with tab_alunos:
    st.subheader("📋 Lista Geral de Inscritos")
    alunos_db = carregar_alunos()
    
    if alunos_db:
        st.dataframe(alunos_db, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum aluno cadastrado ainda.")
