import math

# --- SEU BANCO DE DADOS ATUALIZADO (Preços do arquivo 'Preco raiz.csv') ---
taxas_tiktok = {"percentual": 0.12, "fixa": 4.0}
imposto_aliquota = 0.10 

produtos_raiz = {
    "placa tijolinho": 3.00,
    "placa marmore": 2.20,
    "rodapé": 7.00,
    "piso vinilico": 2.40,
    "ripado rígido": 6.00,
    "marmore em rolo": 24.00,
    "tijolinho resinado": 6.50,
    "fita": 3.60,
    "rodapé pvc": 7.00,
    "im": 11.50,
    "rodapé eva": 21.10,
    "boiserie": 11.30,
    "ripado em rolo": 45.00,
    "cabeceira": 6.51
}

def calcular_v1_minimo(produto, qtd_kit, margem_int, campanha_int):
    # Padroniza o nome para evitar erro de digitação
    nome_busca = produto.lower().strip()
    custo_un = produtos_raiz.get(nome_busca, 0)
    
    if custo_un == 0:
        print(f"\n⚠️ ATENÇÃO: Produto '{produto}' não encontrado! Usando custo R$ 0.00")

    custo_total = (custo_un * qtd_kit) + 1.00 # Rateio Fixo
    
    m = margem_int / 100
    c = campanha_int / 100
    i = imposto_aliquota
    t_pct = taxas_tiktok["percentual"]
    t_fixa = taxas_tiktok["fixa"]

    # FÓRMULA EXATA DA SUA PLANILHA (N2): (CustoTotal + TaxaFixa) / (1 - Margem - TaxaMKT - Campanha - ADS - Imposto)
    # No seu teste: ADS foi 0
    denominador = 1 - m - t_pct - c - 0 - i
    
    if denominador <= 0: return None
    
    preco_venda = (custo_total + t_fixa) / denominador
    return round(preco_venda, 2)

def calcular_v2_promocional(preco_anuncio, preco_minimo, afiliado_int):
    pct_afi = afiliado_int / 100
    # Preço final após desconto de afiliado (Coluna G do seu CSV de Promoção)
    preco_final_venda = preco_anuncio * (1 - pct_afi)
    
    # Disponível para promoção (Coluna J: ARREDONDAR.PARA.BAIXO)
    disponivel_pct = math.floor((1 - (preco_minimo / preco_final_venda)) * 100)
    
    # Preço Promocional (Coluna K)
    preco_promocional = preco_anuncio * (1 - (disponivel_pct / 100))
    
    # Preço após comissão (Coluna L)
    preco_apos_comissao = preco_final_venda - (preco_anuncio * (disponivel_pct / 100))
    
    return {
        "disponivel": disponivel_pct,
        "promocional": round(preco_promocional, 2),
        "recebido": round(preco_apos_comissao, 2)
    }

# --- INTERFACE ---
print("=== CALCULADORA TIKTOK ===")
prod_input = input("Produto: ")
kit = int(input("Quantidade no Kit: "))
margem = float(input("Margem Líquida desejada %: ")) 
campanha = float(input("Desconto Campanha %: "))

p_min = calcular_v1_minimo(prod_input, kit, margem, campanha)

if p_min:
    print(f"\n> PREÇO DE VENDA (MÍNIMO): R$ {p_min}")
    print(f"-------------------------------------------")
    p_anuncio = float(input("Preço de Anúncio (Cadastrar no TikTok) R$: "))
    afi = float(input("Comissão Afiliado %: "))
    
    res = calcular_v2_promocional(p_anuncio, p_min, afi)
    
    print(f"\nESTRATÉGIA DE PROMOÇÃO TIKTOK:")
    print(f"1. No Seller Center, coloque: {res['disponivel']}% de desconto")
    print(f"2. Preço na Vitrine: R$ {res['promocional']}")
    print(f"3. Seu saldo (Líquido): R$ {res['recebido']}")
    print(f"4. Segurança: {'✅ DENTRO DA MARGEM' if res['recebido'] >= p_min else '❌ PREJUÍZO (Aumente o preço de anúncio)'}")