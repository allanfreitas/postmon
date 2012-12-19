from bottle import route, run, response
from CepTracker import CepTracker
from requests import ConnectionError
from correios import Correios

from database import MongoDb as Database

import json

def expired(record_date):
	from datetime import datetime, timedelta

	WEEKS = 26 #6 months

	now = datetime.now()

	return ( now - record_date['v_date'] >= timedelta(weeks=WEEKS))


def _get_info_from_source(cep):
	tracker = CepTracker()
	info = tracker.track(cep)

	if len(info) == 0:
		raise ValueError()

	return info


@route('/cep/<cep:re:\d{5}-?\d{3}>')
def verifica_cep(cep):
	cep = cep.replace('-','')
	db = Database()

	response.headers['Access-Control-Allow-Origin'] = '*'

	try:
		result = db.get_one(cep, fields={ '_id': False })

		if not result or not result.has_key('v_date') or expired(result):
			try:
				for item in _get_info_from_source(cep):
					db.insert_or_update(item)

			except ConnectionError:
				response.status = '503 Servico Temporariamente Indisponivel'

		result = db.get_one(cep, fields={ '_id': False, 'v_date': False })

		response.headers['Cache-Control'] = 'public, max-age=2592000'

	except ValueError:
		response.status = '404 O CEP %s informado nao pode ser localizado' %cep

	return result

@route('/track/ect/<track>')
def track_ect(track):
	try:
		encomenda = Correios.encomenda(track)

		result = []

		for status in encomenda.status:
			resposta = dict()
			
			resposta['data'] = status.data
			resposta['local'] = status.local
			resposta['situacao'] = status.situacao
			resposta['detalhes'] = status.detalhes

			result.append(resposta)

		return json.dumps(result)

	except AttributeError:
		response.status = '404 O pacote %s informado nao pode ser localizado'

def _standalone(port=9876):
    run(host='localhost', port=port)
