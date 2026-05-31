
from pathlib import Path
import cv2
import numpy as np
import matplotlib.pyplot as plt


#já esse arquivo funciona como o cérebro do sistema
#ele faz o pre processamento da imagem, detecta os 
#contornos, estima a quantidade de parafusos, avalia o risco 
#de erro e gera as imagens de resultado e etapas de processamento, 
#tudo isso encapsulado na classe Count_Parafuso que é importada
#e utilizada tanto no run_all.py para processar as imagens do 
#desafio quanto no app.py para a aplicação web.

class Count_Parafuso:
    """Classe responsável por detectar, contar e sinalizar risco de erro."""

    def __init__(self, area_minima_relativa=0.003, area_padrao_parafuso=0.010):
        self.area_minima_relativa = area_minima_relativa
        self.area_padrao_parafuso = area_padrao_parafuso

    def _pre_processar(self, imagem):
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        fundo = cv2.medianBlur(cinza, 51)
        diferenca = cv2.absdiff(cinza, fundo)
        diferenca = cv2.normalize(diferenca, None, 0, 255, cv2.NORM_MINMAX)
        _, mascara_diferenca = cv2.threshold(
            diferenca, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        suavizada = cv2.GaussianBlur(cinza, (5, 5), 0)
        bordas = cv2.Canny(suavizada, 50, 150)
        bordas = cv2.dilate(bordas, np.ones((3, 3), np.uint8), iterations=1)

        mascara = cv2.bitwise_or(mascara_diferenca, bordas)
        mascara = cv2.morphologyEx(
            mascara, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1
        )
        mascara = cv2.morphologyEx(
            mascara, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1
        )
        return cinza, fundo, diferenca, mascara_diferenca, bordas, mascara

    def contar(
        self,
        caminho_imagem,
        salvar_etapas=False,
        salvar_resultado=False,
        pasta_saida="saida",
        pasta_etapas="etapas_processamento",
    ):
        caminho_imagem = Path(caminho_imagem)
        pasta_saida = Path(pasta_saida)
        pasta_etapas = Path(pasta_etapas)

        imagem = cv2.imread(str(caminho_imagem))
        if imagem is None:
            raise FileNotFoundError(f"Não foi possível abrir a imagem: {caminho_imagem}")

        nome_base = caminho_imagem.stem
        altura, largura = imagem.shape[:2]
        area_imagem = altura * largura

        cinza, fundo, diferenca, mascara_diferenca, bordas, mascara = self._pre_processar(imagem)

        contornos, _ = cv2.findContours(
            mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        area_minima = self.area_minima_relativa * area_imagem
        area_maxima = 0.60 * area_imagem
        objetos = []

        for contorno in contornos:
            area = cv2.contourArea(contorno)
            if area < area_minima or area > area_maxima:
                continue

            x, y, w, h = cv2.boundingRect(contorno)
            proporcao = max(w, h) / (min(w, h) + 1e-6)

            if proporcao < 1.08 and area < 0.02 * area_imagem:
                continue

            objetos.append(
                {
                    "contorno": contorno,
                    "area": float(area),
                    "caixa": (x, y, w, h),
                    "proporcao": float(proporcao),
                }
            )

        quantidade, detalhes_estimativa = self._estimar_quantidade(objetos, area_imagem)
        alerta = self._avaliar_risco(objetos, quantidade, mascara, largura, altura)
        confianca = self._calcular_confianca(objetos, quantidade, alerta, largura, altura)

        imagem_contornos = self._desenhar_contornos(imagem, objetos)
        imagem_resultado = self._desenhar_resultado(
            imagem, objetos, quantidade, confianca, alerta, detalhes_estimativa
        )

        dados = {
            "imagem": caminho_imagem.name,
            "quantidade": int(quantidade),
            "confianca": int(confianca),
            "objetos_detectados": len(objetos),
            "alerta": alerta,
            "detalhes_estimativa": detalhes_estimativa,
            "resultado": imagem_resultado,
            "etapas": {
                "original": imagem,
                "cinza": cinza,
                "fundo_estimado": fundo,
                "diferenca_fundo": diferenca,
                "mascara_por_diferenca": mascara_diferenca,
                "bordas": bordas,
                "mascara_final": mascara,
                "contornos": imagem_contornos,
                "resultado": imagem_resultado,
            },
        }

        if salvar_resultado:
            pasta_saida.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(pasta_saida / f"resultado_{nome_base}.jpg"), imagem_resultado)

        if salvar_etapas:
            pasta_etapas.mkdir(parents=True, exist_ok=True)
            self._salvar_etapas(nome_base, dados["etapas"], pasta_etapas)
            self._salvar_painel(nome_base, dados, pasta_etapas)

        return dados

    def _estimar_quantidade(self, objetos, area_imagem):
        if not objetos:
            return 0, {"area_referencia": 0, "estimativas_locais": []}

        areas = np.array([obj["area"] for obj in objetos], dtype=float)

        if len(areas) >= 2:
            limite = np.percentile(areas, 70)
            area_referencia = float(np.median(areas[areas <= limite]))
        else:
            area_referencia = float(self.area_padrao_parafuso * area_imagem)

        quantidade = 0
        estimativas_locais = []

        for obj in objetos:
            area = obj["area"]
            razao = area / max(area_referencia, 1.0)

            if razao >= 1.7:
                estimativa = int(round(razao))
            else:
                estimativa = 1

            estimativa = max(1, min(estimativa, 30))
            quantidade += estimativa
            estimativas_locais.append(
                {
                    "area": round(area, 2),
                    "razao_area": round(razao, 2),
                    "estimativa": int(estimativa),
                }
            )

        return int(quantidade), {
            "area_referencia": round(area_referencia, 2),
            "estimativas_locais": estimativas_locais,
        }

    def _avaliar_risco(self, objetos, quantidade, mascara, largura, altura):
        if not objetos:
            return {
                "revisar": True,
                "nivel": "alto",
                "mensagem": "Nenhum parafuso foi detectado com segurança.",
                "motivos": ["A imagem não gerou objetos válidos para contagem."],
                "recomendacao": "Tire uma nova foto com melhor iluminação e fundo limpo.",
            }

        motivos = []
        areas = np.array([obj["area"] for obj in objetos], dtype=float)
        area_mediana = float(np.median(areas))
        maior_area = float(np.max(areas))
        area_ocupada = cv2.countNonZero(mascara) / float(largura * altura)

        if quantidade > len(objetos):
            motivos.append(
                "A estimativa ficou maior que o número de contornos, indicando possível agrupamento."
            )

        if maior_area / max(area_mediana, 1.0) >= 1.8:
            motivos.append("Existe uma região detectada muito maior que as demais.")

        if len(objetos) <= 4 and area_ocupada > 0.06:
            motivos.append(
                "Poucos contornos ocupam área relevante da imagem, sinal de parafusos muito próximos."
            )

        if any(obj["proporcao"] > 8 for obj in objetos):
            motivos.append("Há região muito alongada ou irregular, possível união de objetos.")

        if motivos:
            nivel = "alto" if len(motivos) >= 2 or len(objetos) <= 4 else "medio"
            return {
                "revisar": True,
                "nivel": nivel,
                "mensagem": "Possível sobreposição ou proximidade excessiva entre parafusos.",
                "motivos": motivos,
                "recomendacao": "A contagem foi informada, mas confira a foto. Se possível, espalhe os parafusos e tire uma nova imagem.",
            }

        return {
            "revisar": False,
            "nivel": "baixo",
            "mensagem": "Leitura sem sinais fortes de agrupamento.",
            "motivos": [],
            "recomendacao": "A contagem pode ser usada normalmente.",
        }

    def _calcular_confianca(self, objetos, quantidade, alerta, largura, altura):
        if quantidade == 0:
            return 0

        confianca = 100

        if alerta["revisar"]:
            confianca -= 22 if alerta["nivel"] == "alto" else 12

        if quantidade > len(objetos):
            confianca -= 8

        for obj in objetos:
            x, y, w, h = obj["caixa"]
            toca_borda = x <= 2 or y <= 2 or (x + w) >= largura - 2 or (y + h) >= altura - 2
            if toca_borda:
                confianca -= 10

        return int(max(20, min(100, confianca)))

    def _desenhar_contornos(self, imagem, objetos):
        saida = imagem.copy()
        for obj in objetos:
            cv2.drawContours(saida, [obj["contorno"]], -1, (0, 255, 255), 2)
        return saida

    def _desenhar_resultado(self, imagem, objetos, quantidade, confianca, alerta, detalhes):
        saida = imagem.copy()

        for i, obj in enumerate(objetos, start=1):
            x, y, w, h = obj["caixa"]
            cv2.rectangle(saida, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(saida, str(i), (x, max(20, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        texto = f"Parafusos: {quantidade} | Confianca: {confianca}%"
        cv2.rectangle(saida, (10, 10), (min(620, 10 + len(texto) * 13), 45), (0, 0, 0), -1)
        cv2.putText(saida, texto, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if alerta["revisar"]:
            aviso = "ALERTA: possivel leitura comprometida"
            cv2.rectangle(saida, (10, 50), (min(760, 10 + len(aviso) * 13), 85), (0, 140, 255), -1)
            cv2.putText(saida, aviso, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        return saida

    def _salvar_etapas(self, nome_base, etapas, pasta_etapas):
        for nome_etapa, imagem in etapas.items():
            cv2.imwrite(str(pasta_etapas / f"{nome_base}_{nome_etapa}.jpg"), imagem)

    def _salvar_painel(self, nome_base, dados, pasta_etapas):
        etapas = dados["etapas"]
        titulos = [
            "1. Original",
            "2. Cinza",
            "3. Diferenca do fundo",
            "4. Mascara final",
            "5. Contornos",
            f"6. Resultado: {dados['quantidade']} | {dados['confianca']}%",
        ]
        chaves = ["original", "cinza", "diferenca_fundo", "mascara_final", "contornos", "resultado"]

        plt.figure(figsize=(13, 8))
        for indice, (titulo, chave) in enumerate(zip(titulos, chaves), start=1):
            plt.subplot(2, 3, indice)
            imagem = etapas[chave]
            if len(imagem.shape) == 2:
                plt.imshow(imagem, cmap="gray")
            else:
                plt.imshow(cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB))
            plt.title(titulo)
            plt.axis("off")

        plt.tight_layout()
        plt.savefig(pasta_etapas / f"{nome_base}_painel_processamento.png", dpi=160)
        plt.close()
