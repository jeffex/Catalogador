# Catalogador de sinais para IQOption
Gerador de lista de sinais para IQOption

## Funções
- Gera lista para mais de um timeframe
- Gera lista para todos os pares ou só para os abertos no momento
- Pode gerar uma segunda lista de sinais no formato aceito pelo bot do telegram [@checkalistabot](http://t.me/checkalistabot "@checkalistabot") para realizar checagem da lista
- Martingale
- Filtro de tendencia

### Formato de saida
**lista de sinais:** TEMPO;PARIDADE;HORA;DIRECAO

**Exemplo**: M5;EURJPY;12:08;CALL

**lista de checagem:** DATA HORA PARIDADE DIRECAO MARTINGALE TIMEFRAME

**Exemplo**: 2021-01-31 05:45:00 AUDCAD-OTC PUT 0GL 5TM

## Requisitos
- python 3
- iqoptionapi
- datetime
- colorama
- numpy
- pandas

## Configuração
1. Instale os módulos necessários usando o pip
`pip3 install -r requirements.txt`

2. Abra o arquivo config.txt e realize as configurações, informando as informações de login da IQOption e as configurações de catalogação.

3. Execute o catalogador com o comando `python3 catalogador.py`

Ao final da execução, sera gerado o arquivo de sinais e opcionalmente o de checagem, ambos na mesma pasta do catalogador.
O nome do arquivo de sinais é informado no arquivo config.txt. Por padrão é lista.csv.
O arquivo de checagem sempre vai ter o mesmo nome do arquivo de sinais adicionado -CHECK no final. Ex: lista.csv-CHECK

**PS: Se procura um bot para executar a lista gerada por esse catalogador, recomendo o [bot-sinais-2.0](https://github.com/jeffex/bot-sinais-2.0 "bot-sinais-2.0")**
