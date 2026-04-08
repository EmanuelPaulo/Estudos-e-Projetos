import streamlit as st
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import re

icon = Image.open("Colaí.png.png")
st.set_page_config(page_title='Plataforma GRUPO MA', page_icon=icon, layout="wide")

fundo_do_site = """
<style>
.stApp {
    background-image: url("https://acdn-us.mitiendanube.com/stores/853/995/themes/common/logo-852124537-1693921118-0fc332af4475bdb9e91df6c0a219df6b1693921119-480-0.webp");
    background-size: 400px;
    background-repeat: no-repeat;
    background-position: center 80%;
    background-attachment: fixed;
}
</style>
"""

utilizadores = {
    "Andrey": "12345",
    "Paulo": "12345",
    "Caio": "12345"
}

PLANILHAS_CONFIG = {
    "Integração": {
        "planilha_id": "1xYB982qOLp3huB9XftzTSeDRFkVzbtnMUYM2zzYc37M",
        "abas": {
            "Relatorio Integração": "Integração",
            "Relatorio Comercial": "Comercial",
            "Relatorio TI": "TI"
        }
    },
    "Produção": {
        "planilha_id": "128V_od1kEkvRrsiYwg9A024aJwybWhqqkYP3igyhEe4",
        "abas": {
            "Relatorio Produção": "Placa",
            "Relatorio Papel de parede": "Papel de parede",
            "Relatorio Tijolinho": "Tijolinho",
        }
    },
    "Expedição": {
        "planilha_id": "129ivmaSBoX4V3ppei_HkmX7SgMj6DfEoqlKgTtb3EKs",
        "abas": {
            "Relatorio Expedição": "Expedição",
            "Relatorio Full": "Full",
            "Relatorio Estoque": "Estoque"
        }
    },
    "Movimentação de carga": {
        "planilha_id": "1Nb-XnmTysT2gVCX2-IQnCGyvJRP5PCixWqzOSMkkIA0",
        "abas": {
            "Relatorio Mov. de carga": "Movimentação de carga"
        }
    }
}

# Função para conectar ao Google Sheets
@st.cache_resource
def conectar_google_sheets():
    try:
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None


def transformar_dados_transpostos(df_raw):
    """
    Transforma a planilha do formato:
    Linhas = Métricas, Colunas = Datas
    Para o formato:
    Colunas = Data, Métrica, Valor
    """
    try:
        # Pegar a primeira coluna (nomes das métricas)
        metricas = df_raw.iloc[:, 0].tolist()
        
        # Pegar as datas (primeira linha, a partir da coluna 1)
        datas = df_raw.columns[1:].tolist()
        
        # Criar lista para armazenar os dados transformados
        dados_transformados = []
        
        # Para cada métrica, pegar os valores por data
        for idx, metrica in enumerate(metricas):
            if pd.isna(metrica) or metrica == "" or metrica == "-":
                continue
                
            # Pegar os valores para esta métrica
            valores = df_raw.iloc[idx, 1:].tolist()
            
            # Para cada data, criar uma linha
            for data, valor in zip(datas, valores):
                if pd.isna(valor) or valor == "" or valor == "-":
                    continue
                
                # Converter valor para número quando possível
                valor_convertido = converter_valor(valor)
                
                dados_transformados.append({
                    'Data': data,
                    'Métrica': metrica,
                    'Valor': valor_convertido,
                    'Valor_Original': valor
                })
        
        df_transformado = pd.DataFrame(dados_transformados)
        
        # Converter datas
        df_transformado['Data'] = pd.to_datetime(df_transformado['Data'], format='%d/%m', errors='coerce')
        
        # Para anos, assumir ano atual (ajustar se necessário)
        ano_atual = datetime.now().year
        df_transformado['Data'] = df_transformado['Data'].apply(lambda x: x.replace(year=ano_atual) if pd.notna(x) else x)
        
        return df_transformado
        
    except Exception as e:
        st.error(f"Erro ao transformar dados: {e}")
        return None

def converter_valor(valor):
    """Converte string para número, tratando formatos brasileiros"""
    if pd.isna(valor) or valor == "" or valor == "-":
        return None
    
    valor_str = str(valor).strip()
    
    # Converter tempo (ex: "16:30")
    if ':' in valor_str and 'R$' not in valor_str:
        try:
            partes = valor_str.split(':')
            horas = int(partes[0])
            minutos = int(partes[1]) if len(partes) > 1 else 0
            return horas + minutos/60
        except:
            return None
    
    # Converter moeda (ex: "R$ 53.882,16")
    if 'R$' in valor_str:
        try:
            valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return float(valor_limpo)
        except:
            return None
    
    # Converter número com vírgula decimal (ex: "8,77")
    if ',' in valor_str:
        try:
            return float(valor_str.replace(',', '.'))
        except:
            return None
    
    # Tentar converter para float diretamente
    try:
        return float(valor_str)
    except:
        return None

# função para carregar dados do formato transposto
@st.cache_data(ttl=300)
def carregar_dados_transpostos(planilha_id, nome_aba):
    """
    Carrega dados de uma planilha no formato transposto (métricas nas linhas, datas nas colunas)
    """
    try:
        client = conectar_google_sheets()
        if client:
            spreadsheet = client.open_by_key(planilha_id)
            
            try:
                worksheet = spreadsheet.worksheet(nome_aba)
            except gspread.WorksheetNotFound:
                available_sheets = [ws.title for ws in spreadsheet.worksheets()]
                st.error(f"Aba '{nome_aba}' não encontrada. Abas disponíveis: {available_sheets}")
                return None
            
            # Carregar todos os valores como lista de listas
            todos_dados = worksheet.get_all_values()
            
            if not todos_dados:
                st.error("Planilha vazia")
                return None
            
            # Criar DataFrame com a primeira linha como cabeçalho
            df_raw = pd.DataFrame(todos_dados[1:], columns=todos_dados[0])
            
            # Transformar do formato transposto para o formato padrão
            df_transformado = transformar_dados_transpostos(df_raw)
            
            return df_transformado
        else:
            return None
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# Função para filtrar dados por métrica específica
def filtrar_por_metrica(df, nome_metrica):
    """Filtra o DataFrame por uma métrica específica"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Buscar métricas que contenham o nome (case insensitive)
    mask = df['Métrica'].str.contains(nome_metrica, case=False, na=False)
    return df[mask].copy()



def dashboard_integracao(df):
    """Dashboard Integração usando dados transformados"""
    st.header("📊 Dashboard Integração")
    
    if df is None or df.empty:
        st.warning("Nenhum dado disponível")
        return
    
    # Gráfico Homem Hora
    df_hh = filtrar_por_metrica(df, "Homem hora")
    if not df_hh.empty:
        st.subheader("⏰ Homem Hora - Dia a Dia")
        fig = px.bar(df_hh, x='Data', y='Valor', 
                     title='Homem Hora por Dia',
                     labels={'Valor': 'Horas', 'Data': 'Data'})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
    
    # Cards dos últimos 7 dias
    st.subheader("📈 Indicadores (Últimos 7 Dias)")
    
    # Filtrar dados dos últimos 7 dias
    ultima_data = df['Data'].max()
    data_limite = ultima_data - timedelta(days=7)
    df_ultimos_7dias = df[df['Data'] >= data_limite]
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Promoções Ativas
    df_promo = filtrar_por_metrica(df_ultimos_7dias, "Numero de promoções ativas")
    if not df_promo.empty:
        with col1:
            total = df_promo['Valor'].sum()
            st.metric("Promoções Ativas (7 dias)", f"{int(total) if total else 0}")
    
    # Anúncios Cadastrados
    df_anuncios_cad = filtrar_por_metrica(df_ultimos_7dias, "Numero de anúncios cadastrados")
    if not df_anuncios_cad.empty:
        with col2:
            total = df_anuncios_cad['Valor'].sum()
            st.metric("Anúncios Cadastrados (7 dias)", f"{int(total) if total else 0}")
    
    # Anúncios Excluídos
    df_anuncios_exc = filtrar_por_metrica(df_ultimos_7dias, "Numero de anúncios excluídos")
    if not df_anuncios_exc.empty:
        with col3:
            total = df_anuncios_exc['Valor'].sum()
            st.metric("Anúncios Excluídos (7 dias)", f"{int(total) if total else 0}")
    
    # Risco de Quebra
    df_risco = filtrar_por_metrica(df, "Produtos com risco de quebra")
    if not df_risco.empty:
        with col4:
            valor_ontem = df_risco[df_risco['Data'] == ultima_data]['Valor']
            risco = valor_ontem.values[0] if not valor_ontem.empty else 0
            st.metric("Risco de Quebra (ontem)", f"{int(risco) if risco else 0} produtos")
    
    st.markdown("---")
    
    # Função para criar gráficos TACOS
    def criar_grafico_tacos(df, nome_metrica, titulo):
        df_metrica = filtrar_por_metrica(df, nome_metrica)
        if not df_metrica.empty:
            st.subheader(f"📈 {titulo}")
            fig = px.line(df_metrica, x='Data', y='Valor', 
                          title=f'{titulo} (Últimos dias)',
                          markers=True)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar último valor
            ultimo_valor = df_metrica.iloc[-1]['Valor']
            if ultimo_valor:
                st.metric(f"💰 Último valor", f"{ultimo_valor:.2f}" if isinstance(ultimo_valor, float) else ultimo_valor)
            return True
        return False
    
    # TACOS Shopee Colai
    if criar_grafico_tacos(df, "TACOS.*SHOPEE COLAI", "TACOS - Shopee Colai"):
        st.markdown("---")
    
    # Saldo ADS Shopee Colai
    df_saldo_sc = filtrar_por_metrica(df, "Saldo ADS SHOPEE COLAI")
    if not df_saldo_sc.empty:
        ultimo_saldo = df_saldo_sc.iloc[-1]['Valor']
        if ultimo_saldo:
            st.metric("💰 Saldo ADS Shopee Colai", f"R$ {ultimo_saldo:,.2f}")
        st.markdown("---")
    
    # TACOS Shopee Papo
    if criar_grafico_tacos(df, "TACOS.*SHOPEE PAPO", "TACOS - Shopee Papo"):
        st.markdown("---")
    
    # Saldo ADS Shopee Papo
    df_saldo_sp = filtrar_por_metrica(df, "Saldo ADS SHOPEE PAPO")
    if not df_saldo_sp.empty:
        ultimo_saldo = df_saldo_sp.iloc[-1]['Valor']
        if ultimo_saldo:
            st.metric("💰 Saldo ADS Shopee Papo", f"R$ {ultimo_saldo:,.2f}")
        st.markdown("---")
    
    # TACOS Mercado Livre
    col1, col2 = st.columns(2)
    with col1:
        criar_grafico_tacos(df, "TACOS.*MERCADO LIVRE COLAI", "TACOS - Mercado Livre Colai")
    with col2:
        criar_grafico_tacos(df, "TACOS.*MERCADO LIVRE PAPO", "TACOS - Mercado Livre Papo")
    
    st.markdown("---")
    
    # TACOS Magalu
    col1, col2 = st.columns(2)
    with col1:
        if criar_grafico_tacos(df, "TACOS.*MAGALU COLAI", "TACOS - Magalu Colai"):
            df_saldo_mc = filtrar_por_metrica(df, "Saldo ADS MAGALU COLAI")
            if not df_saldo_mc.empty:
                ultimo_saldo = df_saldo_mc.iloc[-1]['Valor']
                if ultimo_saldo:
                    st.metric("💰 Saldo ADS Magalu Colai", f"R$ {ultimo_saldo:,.2f}")
    
    with col2:
        if criar_grafico_tacos(df, "TACOS.*MAGALU PAPO", "TACOS - Magalu Papo"):
            df_saldo_mp = filtrar_por_metrica(df, "Saldo ADS MAGALU PAPO")
            if not df_saldo_mp.empty:
                ultimo_saldo = df_saldo_mp.iloc[-1]['Valor']
                if ultimo_saldo:
                    st.metric("💰 Saldo ADS Magalu Papo", f"R$ {ultimo_saldo:,.2f}")

def dashboard_comercial(df):
    st.header("📊 Dashboard Comercial")
    st.info("Dashboard Comercial em desenvolvimento - estrutura similar à Integração")
    if df is not None and not df.empty:
        st.dataframe(df)

def dashboard_ti(df):
    st.header("📊 Dashboard TI")
    st.info("Dashboard TI em desenvolvimento - estrutura similar à Integração")
    if df is not None and not df.empty:
        st.dataframe(df)

def dashboard_producao(df):
    st.header("📊 Dashboard Produção")
    st.info("Dashboard de Produção em desenvolvimento")
    if df is not None and not df.empty:
        st.dataframe(df)

def dashboard_expedicao(df):
    st.header("📊 Dashboard Expedição")
    st.info("Dashboard de Expedição em desenvolvimento")
    if df is not None and not df.empty:
        st.dataframe(df)

def exibir_dashboard(setor, nome_relatorio):
    if setor not in PLANILHAS_CONFIG:
        st.error(f"Setor '{setor}' não configurado!")
        return
    
    config_setor = PLANILHAS_CONFIG[setor]
    planilha_id = config_setor["planilha_id"]
    
    if nome_relatorio not in config_setor["abas"]:
        st.error(f"Relatório '{nome_relatorio}' não encontrado para o setor '{setor}'!")
        return
    
    nome_aba = config_setor["abas"][nome_relatorio]
    
    with st.spinner(f"Carregando dados do relatório {nome_relatorio}..."):
        # Usar a função específica para formato transposto
        df = carregar_dados_transpostos(planilha_id, nome_aba)
    
    if df is None or df.empty:
        st.error(f"Não foi possível carregar os dados para {setor} - {nome_relatorio}.")
        
        # Mostrar exemplo do formato esperado
        with st.expander("📖 Formato esperado da planilha"):
            st.markdown("""
            ### Sua planilha deve estar no seguinte formato:
            
            | (vazio) | 31/03 | 01/04 | 02/04 | ... |
            |---------|-------|-------|-------|-----|
            | Homem hora | 16:30 | 16 | 15 | ... |
            | Numero de promoções ativas | 0 | 0 | 0 | ... |
            | TACOS SHOPEE COLAI | 8,77 | 8,71 | 9,03 | ... |
            | Saldo ADS SHOPEE COLAI | R$ 53.882,16 | - | - | ... |
            
            **Importante:**
            - Primeira coluna: Nomes das métricas
            - Primeira linha: Datas (formato DD/MM)
            - Valores podem ser: números, horas (HH:MM), moedas (R$)
            - Use "-" para valores vazios
            """)
        return
    
    # Exibir dashboard baseado no setor
    if setor == "Integração":
        if nome_relatorio == "Relatorio Integração":
            dashboard_integracao(df)
        elif nome_relatorio == "Relatorio Comercial":
            dashboard_comercial(df)
        elif nome_relatorio == "Relatorio TI":
            dashboard_ti(df)
    elif setor == "Produção":
        if nome_relatorio == "Relatorio Placa":
            dashboard_integracao(df)
        elif nome_relatorio == "Relatorio Papel de parede":
            dashboard_comercial(df)
        elif nome_relatorio == "Relatorio Tijolinho":
            dashboard_ti(df)

    elif setor == "Expedição":
        if nome_relatorio == "Relatorio Expedição":
            dashboard_integracao(df)
        elif nome_relatorio == "Relatorio Full":
            dashboard_comercial(df)
        elif nome_relatorio == "Relatorio Estoque":
            dashboard_ti(df)
    elif setor == "Movimentação de carga":
        if nome_relatorio == "Relatorio Movimentação de carga":
            dashboard_integracao(df)
            
    else:
        st.dataframe(df)

if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_nome = ""

if not st.session_state.logado:
    st.markdown(fundo_do_site, unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 2, 1])
    
    with col_login:
        st.write("")
        st.subheader("Por favor, faça seu login:")
        
        with st.form("form_login"):
            usuario = st.text_input('Usuário:')
            senha = st.text_input('Senha:', type='password')
            submit = st.form_submit_button('ENTRAR', use_container_width=True)
            
            if submit:
        # Limpar espaços em branco
             usuario_limpo = usuario.strip()
             senha_limpa = senha.strip()
        
        # DEBUG: Mostrar o que está sendo digitado (remova depois que funcionar)
           
        
        # Verificar se o usuário existe
            if usuario_limpo in utilizadores:
                st.write(f"🔍 Debug - Usuário encontrado! Verificando senha...")
                if utilizadores[usuario_limpo] == senha_limpa:
                    st.session_state.logado = True
                    st.session_state.usuario_nome = usuario_limpo
                    st.rerun()
                else:
                    st.error('Senha incorreta! Tente novamente.')
            else:
                st.error(f'Usuário "{usuario_limpo}" não encontrado!')

else:
    if 'dashboard_visible' not in st.session_state:
        st.session_state.dashboard_visible = False
    if 'current_relatorio' not in st.session_state:
        st.session_state.current_relatorio = None
    if 'current_setor' not in st.session_state:
        st.session_state.current_setor = None
    
    with st.sidebar:
        st.image("GrupoM.A.png", width=300)
        
        with st.container(border=True):
            st.write(f"👤 Usuário: **{st.session_state.usuario_nome}**")
        st.markdown("---")
        
        st.markdown("### Setor:")
        
        # Lista de setores disponíveis
        setores_disponiveis = list(PLANILHAS_CONFIG.keys())
        opcao_setor = st.selectbox(
            'Escolha o Setor:',
            setores_disponiveis,
            label_visibility="collapsed",
            key="setor_select"
        )
        
        st.markdown("### Relatórios:")
        
        if opcao_setor in PLANILHAS_CONFIG:
            relatorios_disponiveis = list(PLANILHAS_CONFIG[opcao_setor]["abas"].keys())
        else:
            relatorios_disponiveis = []
        
        relatorio_selecionado = st.selectbox(
            'Escolha o Relatório:',
            relatorios_disponiveis,
            label_visibility="collapsed",
            key="relatorio_select"
        )
        
        if st.button("📊 GERAR RELATÓRIO", use_container_width=True, type="primary"):
            if relatorio_selecionado:
                st.session_state.dashboard_visible = True
                st.session_state.current_relatorio = relatorio_selecionado
                st.session_state.current_setor = opcao_setor
                st.rerun()
        
        st.markdown("---")
        
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False
            st.session_state.dashboard_visible = False
            st.rerun()
    
    if st.session_state.dashboard_visible and st.session_state.current_relatorio:
        exibir_dashboard(st.session_state.current_setor, st.session_state.current_relatorio)
    else:
        st.title(f'Olá, {st.session_state.usuario_nome}! 👋')
        st.markdown("### Bem-vindo ao **Painel de Dashboard e Relatórios**")
        st.write("Selecione o setor e o relatório desejado no menu lateral e clique em **GERAR RELATÓRIO** para visualizar os gráficos.")
        st.markdown("---")