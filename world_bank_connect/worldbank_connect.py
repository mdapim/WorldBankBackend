from flask import Flask, jsonify, request, send_file
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask_cors import CORS
import json

load_dotenv()
app = Flask(__name__)
CORS(app)

WB_DBNAME = os.getenv('WB_DBNAME')
WB_HOST = os.getenv('WB_HOST')
WB_PASSWORD = os.getenv('WB_PASSWORD')
WB_USERNAME = os.getenv('WB_USERNAME')


def validate_input(data):
    if len(data) == 0:
        return 'LENGTH=0'
    if len(data['indicator']) == 0:
        return 'NOINDICATORS'
    if len(data['country']) == 0:
        return 'NOCOUNTRY'
    for key in data:
        if type(data[key]) != list:
            return f'NOTARRAY: {key}'
    return 'None'


def get_params(search):
    country_params = tuple(search['country'])
    indicator_params = tuple(search['indicator'])
    start_date = search['range'][0]
    end_date = search['range'][1]
    params = tuple([country_params, indicator_params, start_date, end_date])
    return params


def get_bank_connection():
    try:
        conn = conn = psycopg2.connect(
            f"dbname={WB_DBNAME} user={WB_USERNAME} host={WB_HOST} port = 5432 password={WB_PASSWORD}")
        return conn
    except:
        return False


def convert_data(results, search):
    print(results)
    country_list = search['country']
    indicator_list = search['indicator']
    data_dict = {}
    oldest_year = results[0]['year']
    newest_year = results[-1]['year']
    for indicator in indicator_list:
        data_dict[indicator]=[]
        for year in range(oldest_year,newest_year):
            data_dict[indicator].append({'year':year})
    for result in results:
        indicator = result['indicatorname']
        year = result['year']
        value = result['value']
        for i,data_el in enumerate(data_dict[indicator]):
            if data_el['year']==year:
                data_dict[indicator][i][result['countryname']]=result['value']
                break
    return data_dict


def query_bank_db(query, params=()):
    conn = get_bank_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                data = cursor.fetchall()
            return data
        except:
            return 'Error fetching from Database'
    else:
        return 'No connection'


@app.route('/search', methods=['POST'])
def search():
    error_handler = {'None': '', 'NOINDICATORS': 'Please select an indicator',
                     'LENGTH=0': 'Please select countries and indicator(s),', "NOTARRAY: country": 'Error on country array',
                     "NOTARRAY: indicator": 'Error on indicator array', "NOTARRAY: range": 'Error on range array', 'NOCOUNTRY': 'Please input a country'}
    if request.method == 'POST':
        search = request.json
        error_message = error_handler[validate_input(search)]
        if error_message == '':
            query = "SELECT indicatorname,countryname,value,year FROM public.indicators WHERE countryname IN %s AND indicatorname IN %s AND year BETWEEN %s AND %s"
            params = get_params(search)
            results = query_bank_db(query, params)
            formatted_results = convert_data(results, search)
            if type(results) != str:
                return jsonify(formatted_results)
            else:
                return jsonify({'error': results})
        else:
            return jsonify({'error': error_message})


@app.route('/general', methods=['GET'])
def get_general_info():
    conn = get_bank_connection()
    query_countries = "SELECT tablename from public.countries;"
    query_indicators = "SELECT indicatorname from public.series;"
    countries = query_bank_db(query_countries)
    indicators = query_bank_db(query_indicators)
    if type(countries) != str and type(indicators) != str:
        return jsonify([countries, indicators])
    else:
        return jsonify({'error': 'Querying error'})
