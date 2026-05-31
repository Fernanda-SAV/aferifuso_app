from pathlib import Path
import csv
from contador_parafusos import Count_Parafuso


#esse algotimo vai ser executado para 
#todos os arquivos da pasta imagens_teste que são as 
#imagens do desafio 1, ele vai gerar um arquivo csv com os 
#resultados e também salvar as imagens de resultado e etapas de processamento 
#em pastas separadas para cada imagem, isso facilita a análise e comparação 
#dos resultados posteriormente.

PASTA_IMAGENS = Path("imagens_teste")
PASTA_SAIDA = Path("saida")
PASTA_ETAPAS = Path("etapas_processamento")

contador = Count_Parafuso()
PASTA_SAIDA.mkdir(exist_ok=True)
PASTA_ETAPAS.mkdir(exist_ok=True)

resultados = []

print("\nAFERIFUSO - RESULTADOS DO DESAFIO 1\n")

for imagem in sorted(PASTA_IMAGENS.glob("*.jpg")):
    dados = contador.contar(
        imagem,
        salvar_etapas=True,
        salvar_resultado=True,
        pasta_saida=PASTA_SAIDA,
        pasta_etapas=PASTA_ETAPAS,
    )

    print(f"{imagem.name}: {dados['quantidade']} parafuso(s) | confiança={dados['confianca']}% | contornos={dados['objetos_detectados']}")
    if dados["alerta"]["revisar"]:
        print(f"  ALERTA: {dados['alerta']['mensagem']}")
        for motivo in dados["alerta"]["motivos"]:
            print(f"  - {motivo}")
    print()

    resultados.append({
        "imagem": imagem.name,
        "quantidade": dados["quantidade"],
        "confianca": dados["confianca"],
        "contornos": dados["objetos_detectados"],
        "alerta": dados["alerta"]["mensagem"],
        "revisar": dados["alerta"]["revisar"],
    })

with open(PASTA_SAIDA / "resumo_resultados.csv", "w", newline="", encoding="utf-8") as arquivo:
    campos = ["imagem", "quantidade", "confianca", "contornos", "alerta", "revisar"]
    escritor = csv.DictWriter(arquivo, fieldnames=campos)
    escritor.writeheader()
    escritor.writerows(resultados)

print("Arquivos gerados em: saida/ e etapas_processamento/\n")
