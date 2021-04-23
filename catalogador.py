from iqoptionapi.stable_api import IQ_Option
from datetime import datetime, timedelta
from colorama import init, Fore, Back
from time import time
import sys, os, configparser, requests, json, re
import numpy as np
import pandas as pd

init(autoreset=True)


def Conexao():
	global API
	email = config['email']
	senha = config['senha']
	print('Conectando....')
	API = IQ_Option(email, senha)
	API.connect()

	if API.check_connect():
		print('Conectado com sucesso!')
	else:
		print('Erro ao conectar')
		sys.exit()


def Configuracoes():
	global config
	config = {}
	arquivo = configparser.RawConfigParser()
	arquivo.read('config.txt')

	config['email'] = arquivo.get('CONTA', 'email')
	config['senha'] = arquivo.get('CONTA', 'senha')
	timeframe_str = arquivo.get('CONFIGURACOES', 'timeframe')
	# Transforma a string timeframe em uma lista de inteiros com os timeframes
	config['timeframe'] = list(map(int, timeframe_str.split(',')))
	config['dias'] = arquivo.get('CONFIGURACOES', 'dias')
	config['porcentagem'] = arquivo.get('CONFIGURACOES', 'porcentagem')
	config['martingale'] = arquivo.get('CONFIGURACOES', 'martingale')
	config['todos_pares'] = arquivo.get('CONFIGURACOES', 'todos_pares')
	config['arquivo_saida'] = arquivo.get('CONFIGURACOES', 'arquivo_saida')
	config['check_lista'] = arquivo.get('CONFIGURACOES', 'check_lista')
	config['validar_sinal'] = arquivo.get('CONFIGURACOES', 'validar_sinais')
	config['tendencia'] = arquivo.get('CONFIGURACOES', 'tendencia')
	config['tendencia_porcentagem'] = int(arquivo.get('CONFIGURACOES', 'tendencia_porcentagem'))


def Clear_Screen():
	sistema = os.name
	if sistema == 'nt':
		os.system('cls')
	else:
		os.system('clear')


def cataloga(par, dias, prct_call, prct_put, timeframe, data_atual):
	data = []
	datas_testadas = []
	time_ = time()
	sair = False
	while sair == False:
		velas = API.get_candles(par, (timeframe * 60), 1000, time_)
		velas.reverse()
		posicao = 0
		for x in velas:

			if datetime.fromtimestamp(x['from']).strftime('%Y-%m-%d') != data_atual:
				if datetime.fromtimestamp(x['from']).strftime('%Y-%m-%d') not in datas_testadas:
					datas_testadas.append(datetime.fromtimestamp(x['from']).strftime('%Y-%m-%d'))

				if len(datas_testadas) <= dias:
					x.update({'cor': 'verde' if x['open'] < x['close'] else 'vermelha' if x['open'] > x['close'] else 'doji'})
					if config['tendencia'] == 'S':
						velas_tendencia = velas[posicao:posicao + periodo_ema]
						tendencia = Verificar_Tendencia(velas_tendencia)
						x.update({'tendencia': tendencia})
						data.append(x)
					else:
						data.append(x)
				else:
					sair = True
					break
			posicao += 1

		time_ = int(velas[-1]['from'] - 1)

	analise = {}
	for velas in data:
		horario = datetime.fromtimestamp(velas['from']).strftime('%H:%M')
		if horario not in analise:
			analise.update({horario: {'verde': 0, 'vermelha': 0, 'doji': 0, '%': 0, 'dir': '', 'tendencia': 0, 'contra_verde': 0, 'contra_vermelha': 0}})
		analise[horario][velas['cor']] += 1
		if config['tendencia'] == 'S':
			if velas['cor'] != velas['tendencia']:
				if velas['cor'] == 'verde':
					analise[horario]['contra_verde'] += 1
				else:
					analise[horario]['contra_vermelha'] += 1

		try:
			analise[horario]['%'] = round(100 * (analise[horario]['verde'] / (analise[horario]['verde'] + analise[horario]['vermelha'] + analise[horario]['doji'])))
		except:
			pass

	for horario in analise:
		if analise[horario]['%'] > 50: analise[horario]['dir'] = 'CALL'
		if analise[horario]['%'] < 50: analise[horario]['%'], analise[horario]['dir'] = 100 - analise[horario]['%'], 'PUT '
		if config['tendencia'] == 'S':
			if analise[horario]['dir'] == 'CALL':
				analise[horario]['tendencia'] = int(100 - ((analise[horario]['contra_verde'] / analise[horario]['verde']) * 100))
			else:
				analise[horario]['tendencia'] = int(100 - ((analise[horario]['contra_vermelha'] / analise[horario]['vermelha']) * 100))

	return analise


def Verificar_Tendencia(velas_tendencia):
	fechamento = round(velas_tendencia[0]['close'], 4)
	df = pd.DataFrame(velas_tendencia)
	EMA = df['close'].ewm(span=periodo_ema, adjust=False).mean()
	for data in EMA:
		EMA_line = data

	if EMA_line > fechamento:
		dir = 'vermelha'
	elif fechamento > EMA_line:
		dir = 'verde'
	else:
		dir = False

	return dir


def Obter_Paridades():
	P = API.get_all_open_time()
	paridades = []
	if config['todos_pares'] == 'S':
		for pares in P['digital']:
			paridades.append(pares)
		for pares in P['turbo']:
			paridades.append(pares)
	else:
		for pares in P['digital']:
			if P['digital'][pares]['open'] == True:
				paridades.append(pares)
		for pares in P['turbo']:
			if P['turbo'][pares]['open'] == True:
				paridades.append(pares)

	return np.unique(paridades)


def Obter_Horario_Paridades():
	info_binarias = {}
	info_digitais = {}
	url = 'https://fininfo.iqoption.com/api/graphql'
	arquivo_payload = open('payload_post.txt', 'r')
	requisicao = requests.post(url, data=arquivo_payload)
	dados = json.loads(requisicao.text)
	for data in dados['data']['BinaryOption']:
		if data['type'] == 'Forex' and len(data['schedule']) != 0:
			x = []
			y = {}
			paridade = data['name']
			y['data'] = data['schedule'][0]['from'].split('T')[0]
			y['abertura'] = data['schedule'][0]['from'].split('T')[1].split('-')[0]
			y['fechamento'] = data['schedule'][0]['to'].split('T')[1].split('-')[0]
			x = [y]
			paridade = String_Format(paridade)
			info_binarias[paridade] = x

	for data in dados['data']['DigitalOption']:
		if data['type'] == 'Forex' and len(data['schedule']) != 0:
			x = []
			y = {}
			paridade = data['name']
			y['data'] = data['schedule'][0]['from'].split('T')[0]
			y['abertura'] = data['schedule'][0]['from'].split('T')[1].split('-')[0]
			y['fechamento'] = data['schedule'][0]['to'].split('T')[1].split('-')[0]
			x = [y]
			paridade = String_Format(paridade)
			info_digitais[paridade] = x

	return info_binarias, info_digitais


def String_Format(string_par):
	format_string = string_par.replace('/', '')
	if re.match("[A-Z]{6} .{5}", format_string):
		format_string = format_string.split(' ')
		format_string = format_string[0] + '-OTC'

	return format_string


def Valida_Sinal(info_binarias, info_digitais, horario, paridade, data_atual):
	if paridade in info_binarias:
		if data_atual == info_binarias[paridade][0]['data']:
			abertura = info_binarias[paridade][0]['abertura']
			fechamento = info_binarias[paridade][0]['fechamento']
			# dif_abertura: Retorna um numero positivo caso o horario do sinal seja maior que o horario de abertura da paridade. Ex: Horario do sinal 01:15 e abertura da paridade é de 01:00, irá retornar 15, que é a diferença em minutos.
			dif_abertura = int((datetime.strptime(horario, '%H:%M') - datetime.strptime(abertura, '%H:%M:%S')).total_seconds() / 60)
			# dif_fechamento: O inverso de dif_abertura. retorna um numero negativo (que é a diferença em minutos) se o horario do sinal for menor que o horario de fechamento da paridade.
			dif_fechamento = int((datetime.strptime(horario, '%H:%M') - datetime.strptime(fechamento, '%H:%M:%S')).total_seconds() / 60)
			# Verifica se o sinal esta dentro do horario de funcionamento da paridade, e retorna True caso esteja.
			if dif_abertura > 0 and dif_fechamento < 0:
				return True

	if paridade in info_digitais:
		if data_atual == info_digitais[paridade][0]['data']:
			abertura = info_digitais[paridade][0]['abertura']
			fechamento = info_digitais[paridade][0]['fechamento']
			# dif_abertura: Retorna um numero positivo caso o horario do sinal seja maior que o horario de abertura da paridade. Ex: Horario do sinal 01:15 e abertura da paridade é de 01:00, irá retornar 15, que é a diferença em minutos.
			dif_abertura = int((datetime.strptime(horario, '%H:%M') - datetime.strptime(abertura, '%H:%M:%S')).total_seconds() / 60)
			# dif_fechamento: O inverso de dif_abertura. retorna um numero negativo (que é a diferença em minutos) se o horario do sinal for menor que o horario de fechamento da paridade.
			dif_fechamento = int((datetime.strptime(horario, '%H:%M') - datetime.strptime(fechamento, '%H:%M:%S')).total_seconds() / 60)
			# Verifica se o sinal esta dentro do horario de funcionamento da paridade, e retorna True caso esteja.
			if dif_abertura > 0 and dif_fechamento < 0:
				return True
	# Retorna False caso não satisfaça nenhuma condição
	return False


def Escreve_Arquivo(arquivo_saida, timeframe, par, horario, direcao, data_atual, martingale):
	open(arquivo_saida, 'a').write('M' + str(timeframe) + ';' + par + ';' + horario + ';' + direcao + '\n')
	if check_lista == 'S':
		open(str(arquivo_saida) + '-CHECK', 'a').write(f'{data_atual} {str(horario) + ":00"} {par} {direcao} {str(martingale) + "GL"} {str(timeframe) + "TM"}\n')


Clear_Screen()
print('=========================================\n|         CATALOGADOR DE SINAIS         |\n=========================================')


try:
	Configuracoes()
	Conexao()

	arquivo_saida = config['arquivo_saida']
	check_lista = config['check_lista']
	timeframe_config = config['timeframe']
	dias = int(config['dias'])
	porcentagem = int(config['porcentagem'])
	martingale = config['martingale']
	prct_call = abs(porcentagem)
	prct_put = abs(100 - porcentagem)
	periodo_ema = 20
	paridades = Obter_Paridades()
	data_atual = datetime.now().strftime('%Y-%m-%d')
	info_binarias, info_digitais = Obter_Horario_Paridades()
	print(f'{Fore.GREEN}>>>>>CATALOGANDO {len(paridades)} PARIDADES EM {len(timeframe_config)} TIMEFRAME(S)<<<<<')
	for timeframe in timeframe_config:
		catalogacao = {}
		contador = 1
		for par in paridades:
			timer = int(time())
			print(f'{contador} - {Fore.GREEN}CATALOGANDO - {Fore.RESET} {Fore.BLUE}{par}{Fore.RESET} | TIMEFRAME {Fore.GREEN}M{timeframe}{Fore.RESET}...', end='')
			catalogacao.update({par: cataloga(par, dias, prct_call, prct_put, timeframe, data_atual)})

			for par in catalogacao:
				for horario in sorted(catalogacao[par]):
					if martingale.strip() != '':

						mg_time = horario
						soma = {'verde': catalogacao[par][horario]['verde'], 'vermelha': catalogacao[par][horario]['vermelha'], 'doji': catalogacao[par][horario]['doji']}

						for i in range(int(martingale)):

							catalogacao[par][horario].update({'mg' + str(i + 1): {'verde': 0, 'vermelha': 0, 'doji': 0, '%': 0}})

							mg_time = str(datetime.strptime((datetime.now()).strftime('%Y-%m-%d ') + str(mg_time), '%Y-%m-%d %H:%M') + timedelta(minutes=timeframe))[11:-3]

							if mg_time in catalogacao[par]:
								catalogacao[par][horario]['mg' + str(i + 1)]['verde'] += catalogacao[par][mg_time]['verde'] + soma['verde']
								catalogacao[par][horario]['mg' + str(i + 1)]['vermelha'] += catalogacao[par][mg_time]['vermelha'] + soma['vermelha']
								catalogacao[par][horario]['mg' + str(i + 1)]['doji'] += catalogacao[par][mg_time]['doji'] + soma['doji']

								catalogacao[par][horario]['mg' + str(i + 1)]['%'] = round(100 * (catalogacao[par][horario]['mg' + str(i + 1)]['verde' if catalogacao[par][horario]['dir'] == 'CALL' else 'vermelha'] / (catalogacao[par][horario]['mg' + str(i + 1)]['verde'] + catalogacao[par][horario]['mg' + str(i + 1)]['vermelha'] + catalogacao[par][horario]['mg' + str(i + 1)]['doji'])))

								soma['verde'] += catalogacao[par][mg_time]['verde']
								soma['vermelha'] += catalogacao[par][mg_time]['vermelha']
								soma['doji'] += catalogacao[par][mg_time]['doji']
							else:
								catalogacao[par][horario]['mg' + str(i + 1)]['%'] = 0

			print('finalizado em ' + str(int(time()) - timer) + ' segundos')
			contador += 1

		print('\n\n')

		for par in catalogacao:
			for horario in sorted(catalogacao[par]):
				ok = False
				if config['tendencia'] == 'S':
					if catalogacao[par][horario]['tendencia'] >= config['tendencia_porcentagem'] and catalogacao[par][horario]['%'] >= porcentagem:
						ok = True

				else:
					if catalogacao[par][horario]['%'] >= porcentagem:
						ok = True
					else:
						for i in range(int(martingale)):
							if catalogacao[par][horario]['mg' + str(i + 1)]['%'] >= porcentagem:
								ok = True
								break

				if ok == True:

					msg = Fore.YELLOW + par + Fore.RESET + ' - ' + horario + ' - ' + (Fore.RED if catalogacao[par][horario]['dir'] == 'PUT ' else Fore.GREEN) + catalogacao[par][horario]['dir'] + Fore.RESET + ' - ' + str(catalogacao[par][horario]['%']) + '% - ' + Back.GREEN + Fore.BLACK + str(catalogacao[par][horario]['verde']) + Back.RED + Fore.BLACK + str(catalogacao[par][horario]['vermelha']) + Back.RESET + Fore.RESET + str(catalogacao[par][horario]['doji'])

					if martingale.strip() != '':
						for i in range(int(martingale)):
							if str(catalogacao[par][horario]['mg' + str(i + 1)]['%']) != 'N/A':
								msg += ' | MG ' + str(i + 1) + ' - ' + str(catalogacao[par][horario]['mg' + str(i + 1)]['%']) + '% - ' + Back.GREEN + Fore.BLACK + str(catalogacao[par][horario]['mg' + str(i + 1)]['verde']) + Back.RED + Fore.BLACK + str(catalogacao[par][horario]['mg' + str(i + 1)]['vermelha']) + Back.RESET + Fore.RESET + str(catalogacao[par][horario]['mg' + str(i + 1)]['doji'])
							else:
								msg += ' | MG ' + str(i + 1) + ' - N/A - N/A'
					print(msg)
					direcao = catalogacao[par][horario]['dir'].strip()
					if config['validar_sinal'] == 'S':
						if Valida_Sinal(info_binarias, info_digitais, horario, par, data_atual):
							Escreve_Arquivo(arquivo_saida, timeframe, par, horario, direcao, data_atual, martingale)
					else:
						Escreve_Arquivo(arquivo_saida, timeframe, par, horario, direcao, data_atual, martingale)

except KeyboardInterrupt:
	sys.exit()
