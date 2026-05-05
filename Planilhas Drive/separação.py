import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re
import time
import os

PASTA_ID_FULL = "1FlCl6QmAtwCCjOpzc58gghvW7FXa6Rr_"
ARQUIVOS_CREDENCIAIS = "creds.json" 

TOKEN_TINY = os.getenv("TOKEN_TINY") 


def planilhas_de_separação(mes_escolhido):


    def conectar_google_services():
        print("   ...Autenticando...")
        escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(ARQUIVOS_CREDENCIAIS, scopes=escopos)
        return build('drive', 'v3', credentials=creds), gspread.authorize(creds)


        
    def buscar_id_pasta_ou_arquivo(service, parent_id, nome_contem, mime_type=None):
        q = f"'{parent_id}' in parents and name contains '{nome_contem}' and trashed = false"
        if mime_type:
            if mime_type == "excel_ou_sheet":
                q += " and (mimeType = 'application/vnd.google-apps.spreadsheet' or mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')"
            else:
                q += f" and mimeType = '{mime_type}'"
        res = service.files().list(q=q, fields="files(id, name, mimeType)", supportsAllDrives=True, includeItemsFromAllDrives=True, orderBy="modifiedTime desc").execute()
        items = res.get('files', [])
        return items[0] if items else None



    def encontrar_aba_correta(sku, titulos_abas):
        sku = sku.strip().upper()

        if sku.endswith("-10M") and "10M" in titulos_abas: return "10M"
        if re.search(r'\d+P$', sku) and "FULL P" in titulos_abas: return "FULL P"

        for medida in ["50X50", "25X25"]:
            if medida in sku:
                for nome_aba in titulos_abas:
                    aba_up = nome_aba.upper()
                    if medida in aba_up:
                        return nome_aba
        prefixo = sku[:4]
        for nome_aba in titulos_abas:
            if prefixo in nome_aba.upper():
                if not re.match(r'^\d+[xX]\d+$', nome_aba): 
                    return nome_aba
        
        for nome_aba in titulos_abas:
            if prefixo in nome_aba.upper():
                if not re.match(r'^\d+[xX]\d+$', nome_aba): return nome_aba
                
    
        match_medida = re.search(r'(\d+[xX]\d+)', sku, re.IGNORECASE)
        if match_medida:
            medida = match_medida.group(1).upper()
            if medida in titulos_abas: return medida
            

        if sku in titulos_abas: return sku
        return None

    def encontrar_full_pronto_generico(service, mes_escolhido):
        meses = ["", "01-jan", "02-fev", "03-mar", "04-abr", "05-mai", "06-jun", "07-jul", "08-ago", "09-set", "10-out", "11-nov", "12-dez"]
        
    
        nome_mes = meses[mes_escolhido]
        
        print(f" 1. Buscando pasta do mês: {nome_mes}...")
        pasta_mes = buscar_id_pasta_ou_arquivo(service, PASTA_ID_FULL, nome_mes, "application/vnd.google-apps.folder")
        if not pasta_mes: return None
        
        print("2. Buscando pasta 'AT'...")
        pasta_at = buscar_id_pasta_ou_arquivo(service, pasta_mes['id'], "AT", "application/vnd.google-apps.folder")
        if not pasta_at: return None
        
        print(" 3. Buscando arquivo 'FULL PRONTO'...")
        arq_pronto = buscar_id_pasta_ou_arquivo(service, pasta_at['id'], "FULL PRONTO", "application/vnd.google-apps.spreadsheet")
        return arq_pronto

    def extrair_kit(sku):
        match = re.search(r'K(\d+)$', sku, re.IGNORECASE)
        if match: return match.group(1)
        return "1"

    def clonar_linha_anterior(ws, linha_origem_idx, linha_destino_start, qtd_linhas):
        if linha_origem_idx < 1: return 
        sheet_id = ws.id
        source_index = linha_origem_idx - 1 
        dest_start_index = linha_destino_start - 1
        
        body = {
            "requests": [{
                "copyPaste": {
                    "source": {
                        "sheetId": sheet_id,
                        "startRowIndex": source_index, "endRowIndex": source_index + 1,
                        "startColumnIndex": 0, "endColumnIndex": 20
                    },
                    "destination": {
                        "sheetId": sheet_id,
                        "startRowIndex": dest_start_index, "endRowIndex": dest_start_index + qtd_linhas,
                        "startColumnIndex": 0, "endColumnIndex": 20
                    },
                    "pasteType": "PASTE_NORMAL", "pasteOrientation": "NORMAL"
                }
            }]
        }
        ws.spreadsheet.batch_update(body)

    def distribuir_separacao(service, client, id_origem_resumo):
        print("\n🚀 INICIANDO DISTRIBUIÇÃO...")
        
        sh_origem = client.open_by_key(id_origem_resumo)
        aba_consulta = sh_origem.get_worksheet(2) 
        print(f"   Lendo dados da aba: {aba_consulta.title}")
        
        dados = aba_consulta.get_all_values()
        lista_cargas = []
        for linha in dados[1:]:
            if len(linha) >= 2 and linha[0]:
                sku = linha[0].strip()
            try:
                qtd = int(float(linha[1].strip().replace(',', '.'))) 
            except:
                qtd = linha[1].strip()
                
            if sku and (qtd or qtd == 0): 
                    lista_cargas.append((sku, qtd))

        file_meta = service.files().get(fileId=id_origem_resumo, fields="parents", supportsAllDrives=True).execute()
        id_pasta_dia = file_meta['parents'][0]

        REGRAS = {
            "Full Placa": ["PLACAS"], 
            "Full Adesivo": ["FINAL_P", "10M"], 
            "Full Colorido": ["COLORIDOS"]
        }

        for pasta_nome, regra in REGRAS.items():
            print(f"\nPasta: {pasta_nome} (Regra: {regra})")
            
            pasta_obj = buscar_id_pasta_ou_arquivo(service, id_pasta_dia, pasta_nome, "application/vnd.google-apps.folder")
            if not pasta_obj: print("   ⚠️ Pasta não encontrada."); continue
                
            planilha_obj = buscar_id_pasta_ou_arquivo(service, pasta_obj['id'], "separação", "excel_ou_sheet")
            if not planilha_obj: print("   ⚠️ Planilha 'separação' não encontrada."); continue
            
            print(f"   ✅ Planilha Alvo: {planilha_obj['name']}")
            
            try:
                sh_dest = client.open_by_key(planilha_obj['id'])
            except Exception as e:
                print(f"   ❌ Erro ao abrir: {e}"); continue

            abas_titulos = [w.title.strip() for w in sh_dest.worksheets()]
            #print(f" [DEBUG] Abas que existem na planilha: {abas_titulos}" )
            itens_validos = []
            for sku, qtd in lista_cargas:
                sku = sku.upper()
                
                pvc_especial = "50X50COM" in sku or "25X25COM" in sku
                
                eh_p = bool(re.search(r'\d+P$', sku))
                eh_10M = sku.endswith("-10M")
                eh_medida_geral = bool(re.search(r'\d+[xX]\d+', sku))
                

                eh_medida = eh_medida_geral and not pvc_especial
                
            
                eh_placa = (not eh_p and not eh_medida and not sku.endswith("-10M")) or pvc_especial
                
                aceitar = False
                if "FINAL_P" in regra and eh_p: aceitar = True
                elif "10M" in regra and eh_10M: aceitar = True
                elif "COLORIDOS" in regra and eh_medida: aceitar = True
                elif "PLACAS" in regra and eh_placa: aceitar = True
                
                if aceitar: itens_validos.append((sku, qtd))
            
            if not itens_validos: print("      Nenhum item."); continue

            por_aba = {}
            for sku, qtd in itens_validos:
                aba_nome = encontrar_aba_correta(sku, abas_titulos)
                if aba_nome:
                    if aba_nome not in por_aba: por_aba[aba_nome] = []
                    por_aba[aba_nome].append((sku, qtd))
            
                    #print(f"[DEBUG] o sku {sku} foi aceito na regra mas não achou uma aba compativel")
            for aba_nome, itens in por_aba.items():
                try:
                    print(f"    Aba '{aba_nome}': processando {len(itens)} itens...")
                    ws = sh_dest.worksheet(aba_nome)
                    all_vals = ws.get_all_values()
                    time.sleep(1.0)
                    
            
                    idx_col_qtd = 2  
                    idx_col_kit = 1  
                    for r_idx in range(min(5, len(all_vals))):
                        linha = all_vals[r_idx]
                        for c_idx, celula in enumerate(linha):
                            txt = str(celula).upper().strip()
                            if "QUANT" in txt or "QTD" in txt: idx_col_qtd = c_idx
                            if "KIT" in txt: idx_col_kit = c_idx

            
                    mapa_existentes = {}
                    idx_total = len(all_vals)
                    for i, r in enumerate(all_vals):
                        if r and len(r) > 0:
                            primeira_celula = str(r[0]).strip().upper()
                        
                            if "TOTAL" in primeira_celula: 
                                idx_total = i
                                break

                    mapa_existentes = {}
            
                    for i in range(2, idx_total):
                        val_a = str(all_vals[i][0]).strip()
                        if val_a:
                            mapa_existentes[val_a] = i

                    batch_updates = []
                    novos_itens = []
                    cursor_vaga = 2 

                    for sku, qtd in itens:
                        valor_kit = extrair_kit(sku) if "Full Placa" in pasta_nome else ""
                        
                        if sku in mapa_existentes:
                    
                            idx_ex = mapa_existentes[sku]
                            l_ex = idx_ex + 1
                            batch_updates.append({'range': f'{chr(65+idx_col_qtd)}{l_ex}', 'values': [[qtd]]})
                        else:
                        
                            vaga_encontrada = -1
                            for tmp in range(cursor_vaga, idx_total):
                                celula_vazia = (all_vals[tmp][0].strip() == "") if tmp < len(all_vals) else True
                                if celula_vazia:
                                    vaga_encontrada = tmp
                                    cursor_vaga = tmp + 1
                                    break
                            
                            if vaga_encontrada != -1:
                            
                                l_vaga = vaga_encontrada + 1
                                batch_updates.append({'range': f'A{l_vaga}', 'values': [[sku]]})
                                batch_updates.append({'range': f'{chr(65+idx_col_qtd)}{l_vaga}', 'values': [[qtd]]})
                                batch_updates.append({'range': f'{chr(65+idx_col_kit)}{l_vaga}', 'values': [[valor_kit]]})
                        
                                all_vals[vaga_encontrada][0] = sku 
                            else:
                        
                                novos_itens.append((sku, qtd, valor_kit))


                    if batch_updates:
                        ws.batch_update(batch_updates, value_input_option='USER_ENTERED')

                
                    if novos_itens:
                
                        linha_insercao = idx_total + 1 
                        
                        print(f"      Inserindo {len(novos_itens)} novas linhas na posição {linha_insercao}")
                        
                    
                        ws.insert_rows([[""]*2] * len(novos_itens), row=linha_insercao, inherit_from_before=True)
                        
                    
                        if linha_insercao > 2:
                            clonar_linha_anterior(ws, linha_insercao - 1, linha_insercao, len(novos_itens))
                        
                        
                        batch_novos = []
                        for i, (s, q, k) in enumerate(novos_itens):
                            l_atual = linha_insercao + i
                            batch_novos.append({'range': f'A{l_atual}', 'values': [[s]]})
                            batch_novos.append({'range': f'{chr(65+idx_col_qtd)}{l_atual}', 'values': [[q]]})
                            batch_novos.append({'range': f'{chr(65+idx_col_kit)}{l_atual}', 'values': [[k]]})
                        
                        ws.batch_update(batch_novos, value_input_option='USER_ENTERED')

                except Exception as e:
                    print(f"      ❌ Erro na aba {aba_nome}: {e}"); time.sleep(5)


            abas_titulos = [w.title.strip() for w in sh_dest.worksheets()]


    service, client = conectar_google_services()
    arquivo_origem = encontrar_full_pronto_generico(service, mes_escolhido)

    if arquivo_origem:
        print(f"Arquivo Origem: {arquivo_origem['name']}")
        distribuir_separacao(service, client, arquivo_origem['id'])
        return("\n✅ Processo Finalizado!")
    else:
        return("❌ Não encontrei o arquivo 'FULL PRONTO'.")