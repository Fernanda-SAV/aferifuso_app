# Aferifuso

Sistema Inteligente de Contagem de Parafusos para apoio ao processo de picking industrial.

A solução utiliza visão computacional clássica com OpenCV, sem treinamento de redes neurais, pois o conjunto fornecido possui poucas imagens e o objetivo é manter baixo custo computacional para uso em dispositivos móveis.

## Estrutura

```text
aferifuso_app/
├── app.py
├── contador_parafusos.py
├── run_all.py
├── requirements.txt
├── imagens_teste/
├── testes_extra/
├── saida/
└── etapas_processamento/
```

As pastas `saida/` e `etapas_processamento/` começam vazias. Elas são preenchidas somente quando executa `python run_all.py`. Como já foi executado no teste do código, elas já se apresentam aqui preenchidas.

## Instalação local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Rodar os testes com as imagens fornecidas

```powershell
python run_all.py
```

## Abrir o aplicativo

```powershell
streamlit run app.py
```

O aplicativo permite:

- selecionar imagem da galeria;
- tirar foto no momento;
- visualizar quantidade estimada;
- visualizar confiança;
- receber alerta quando houver possível sobreposição ou proximidade excessiva entre parafusos;
- visualizar as etapas do processamento.

## Observação importante

Quando os parafusos estão muito agrupados, o sistema informa a contagem estimada, mas emite alerta para o trabalhador conferir a imagem. O sistema não consegue diferenciar muito bem quando os parafusos estão muito próximos, levando-o a crê que se trata de um único parafuso. Isso evita apresentar uma leitura incerta como se fosse totalmente segura.
