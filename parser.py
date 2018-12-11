import os
import re
import json
import sys
import time

from argparse import ArgumentParser
from collections import OrderedDict
from datetime import datetime, timedelta
from urllib import parse

__author__ = "e.calligari"

__maintainer__ = "a.bandini"
__email__ = "alberto.bandini@consulenti.cedacri.it"

rules = {
    "core": re.compile('.*\s+transaction start time\s+(?P<ts>\d{4}\-\d{2}\-\d{2}\s\d{2}\:\d{2}\:\d{2})(?:\.\d+)?\s+ip\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})\s+(?:.*\s+){1,3}wirejustification\s+(?P<desc>.*)\s+(?:.*\s+)wireamount\s+(?P<amount>.*)\s+(?:.*\s+)wirebeneficiaryiban\s+(?P<iban_dst>.*)\s+(?:.*\s+){1,20}wirepayeriban\s+(?P<iban_src>.*)\s+(?:.*\s+)wirepayername\s+(?P<name>.*)\s+(?:.*\s+){1,50}id\s+(?P<user_id>.*)'),
    "ihb": re.compile('.*\s+transaction start time\s+(?P<ts>\d{4}\-\d{2}\-\d{2}\s\d{2}\:\d{2}\:\d{2})(?:\.\d+)?\s+ip\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})\s+(?:.*\s+){1,3}ihb_bt_iban_sepa_src_ord\s+(?P<name>.*)\s+(?:.*\s+)ihb_bt_iban_sepa_src\s+(?P<iban_src>.*)\s+(?:.*\s+)ihb_bt_iban_sepa_dst\s+(?P<iban_dst>.*)\s+(?:.*\s+)+ihb_bt_description\s+(?P<desc>.*)\s+(?:.*\s+)ihb_bt_btamount\s+(?P<amount>.*)\s+(?:.*\s+)+id\s+(?P<user_id>.*)'),
    "new": re.compile('.*\s+transaction start time\s+(?P<ts>\d{4}\-\d{2}\-\d{2}\s\d{2}\:\d{2}\:\d{2})(?:\.\d+)?\s+ip\s+(?P<ip>(?:\d{1,3}\.){3}\d{1,3})\s+(?:.*\s+){1,10}/(?:.*?/){3}(?P<user_id>.*?)/(?:.*?/)+\s+(?:.*\s+){1,3}(?P<json>\{(?:[^{}]*)\})')
}

if __name__ == "__main__":
    # Added identification of DST, so that time is always converted accurately from UTC to local.
    time_offset = 1
    if time.localtime().tm_isdst:
        time_offset = 2

    parser = ArgumentParser()
    parser.add_argument('--site', action='store',
                        required=True,
                        help="Tipologia del sito. Possibili valori: \n{}".format('\n'.join(rules.keys())))
    parser.add_argument('-i', dest='inputfile', action='store', required=True, help="Path del file da parsare.")
    args = parser.parse_args()

    try:
        rule = rules[args.site]
    except KeyError:
        print("ERRORE: Tipologia sito non valida. "
              "Possibili valori: {}".format(", ".join(rules.keys())))
        sys.exit(-1)

    with open(os.path.abspath(args.inputfile)) as f:
        blob = f.read()

    parsed = rule.match(blob)
    
    try:
        parsed.groups()
    except AttributeError:
        print("ERRORE: impossibile parsare correttamente il file con il metodo specificato. Controllare il formato del file o provare un metodo differente")
        sys.exit(-2)

    d = OrderedDict()

    d['Time'] = (datetime.strptime(parsed.group('ts'),
                                   "%Y-%m-%d %H:%M:%S") +
                 timedelta(hours=time_offset)).strftime("%Y-%m-%d %H:%M:%S")
    d['Ordinante'] = ''
    d['IBAN Intestatario'] = ''
    d['Utente'] = parsed.group('user_id')
    d['IP Sorgente'] = parsed.group('ip')
    d['IBAN Beneficiario'] = ''
    d['Causale'] = ''
    d['Importo'] = ''

    try:
        # new site case
        values = json.loads(parsed.group('json'))
        d['Ordinante'] = values['nomeBeneficiario']
        d['IBAN Intestatario'] = values['contoAddebitoIban']
        d['IBAN Beneficiario'] = values['ibanBeneficiario']
        d['Causale'] = values['causale']
        d['Importo'] = values['importo']
    except ValueError:
        print("ERRORE: json malformato")
        sys.exit(-3)
    except IndexError:
        # ihb/core case
        d['Ordinante'] = parsed.group('name')
        d['IBAN Intestatario'] = parsed.group('iban_src')
        d['IBAN Beneficiario'] = parsed.group('iban_dst')
        d['Causale'] = parsed.group('desc')
        d['Importo'] = parsed.group('amount')
        
    for k, v in d.items():
        print("-{}: {}".format(k, parse.unquote(v)))     # Added unquote function, to remove %20 and other annoying formatting
    
