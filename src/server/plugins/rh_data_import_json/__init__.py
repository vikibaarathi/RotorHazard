'''JSON data importer'''

import logging
import json
import RHUtils
import Database
from data_import import DataImporter
from Database import ProgramMethod

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for importer in discover():
            args['registerFn'](importer)

def __(arg): # Replaced with outer language.__ during initialize()
    return arg

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('Import_Initialize', 'Import_register_JSON', registerHandlers, {}, 75)
    if '__' in kwargs:
        __ = kwargs['__']

def import_json(RHAPI, source, args):
    if not source:
        return False

    try:
        data = json.loads(source)
    except Exception as ex:
        logger.error("Unable to import file: {}".format(str(ex)))
        return False

    if "Pilot" in data:
        logger.debug("Importing Pilots...")

        if 'reset_pilots' in args and args['reset_pilots']:
            RHAPI.db.pilots_clear()

        db_pilots = RHAPI.db.pilots

        for input_pilot in data["Pilot"]:

            input_pilot["source_id"] = input_pilot['id']

            db_match = None
            for db_pilot in db_pilots:
                if db_pilot.callsign == input_pilot["callsign"]:
                    db_match = db_pilot
                    break

            if db_match:
                input_pilot["pilot_id"] = db_match.id
                db_pilot, _ = RHAPI.db.pilot_alter(input_pilot)
            else:
                db_pilot = RHAPI.db.pilot_add(input_pilot)

            input_pilot['db_id'] = db_pilot.id

    if "RaceFormat" in data:
        logger.debug("Importing Formats...")

        if 'reset_formats' in args and args['reset_formats']:
            RHAPI.db.raceformats_clear()

        db_formats = RHAPI.db.raceformats

        for input_format in data["RaceFormat"]:
            db_match = None
            for db_format in db_formats:
                if db_format.name == input_format["name"]:
                    db_match = db_format
                    break

            input_format["format_name"] = input_format["name"]

            if db_match:
                input_format["format_id"] = db_match.id
                db_format, _ = RHAPI.db.raceformat_alter(input_format)
            else:
                db_format = RHAPI.db.raceformat_add(input_format)

            input_format['db_id'] = db_format.id

    if "Profiles" in data:
        logger.debug("Importing Profiles...")

        if 'reset_profiles' in args and args['reset_profiles']:
            RHAPI.db.frequencysets_clear()

        db_profiles = RHAPI.db.frequencysets

        for input_profile in data["Profiles"]:
            db_match = None
            for db_profile in db_profiles:
                if db_profile.name == input_profile["name"]:
                    db_match = db_profile
                    break

            input_profile["profile_name"] = input_profile["name"]
            input_profile["profile_description"] = input_profile["description"]

            if db_match:
                input_profile["profile_id"] = db_match.id
                db_profile = RHAPI.db.frequencyset_alter(input_profile)
            else:
                db_profile = RHAPI.db.frequencyset_add(input_profile)

            input_profile['db_id'] = db_profile.id

    if "GlobalSettings" in data:
        logger.debug("Importing Settings...")

        invalid_settings = [
            'server_api',
            'secret_key',
            'currentProfile',
            'currentFormat',
            'eventResults',
            'eventResults_cacheStatus',
        ]

        for setting in data["GlobalSettings"]:
            if setting["option_name"] not in invalid_settings:
                RHAPI.db.option_set(setting["option_name"], setting["option_value"])

    if "RaceClass" in data:
        logger.debug("Importing Classes/Heats...")

        if 'reset_classes' in args and args['reset_classes']:
            RHAPI.db.heats_clear()
            RHAPI.db.raceclasses_clear()
            RHAPI.db.races_clear()

        db_race_classes = RHAPI.db.raceclasses

        for input_race_class in data["RaceClass"]:
            db_match = None
            for db_race_class in db_race_classes:
                if db_race_class.name == input_race_class["name"]:
                    db_match = db_race_class
                    break

            input_race_class["source_id"] = input_race_class['id']

            input_race_class["class_name"] = input_race_class["name"]
            input_race_class["class_description"] = input_race_class["description"]
            input_race_class["class_format"] = input_race_class["format_id"] # db_id
            input_race_class["heat_advance"] = input_race_class["heatAdvanceType"]

            if db_match:
                input_race_class["class_id"] = db_match.id
                db_race_class, _ = RHAPI.db.raceclass_alter(input_race_class)
            else:
                db_race_class = RHAPI.db.raceclass_add(input_race_class)

            input_race_class['db_id'] = db_race_class.id

            if "Heat" in data:
                for input_heat in data['Heat']:
                    if input_heat['class_id'] == input_race_class['source_id']:
                        input_heat['source_id'] = input_heat['id']

                        input_heat['class_id'] = input_race_class['db_id']

                        db_heat = RHAPI.db.heat_add(input_heat)

                        input_heat['db_id'] = db_heat.id

    if "HeatNode" in data and "Heat" in data and "RaceClass" in data:
        logger.debug("Updating HeatNodes...")

        batch = []

        for input_heatnode in data["HeatNode"]:
            db_heatnodes = RHAPI.db.slots

            for heat in data['Heat']:
                if 'source_id' in heat and heat['source_id'] == input_heatnode['heat_id']:
                    for heatnode in db_heatnodes:
                        if heatnode.heat_id == heat['db_id'] and heatnode.node_index == input_heatnode['node_index']: 
                            input_heatnode['slot_id'] = heatnode.id 

                            if input_heatnode['method'] == ProgramMethod.ASSIGN:
                                input_heatnode['pilot'] = RHUtils.PILOT_ID_NONE
                                if 'Pilot' in data:
                                    for p in data['Pilot']:
                                        if p['source_id'] == input_heatnode['pilot_id']:
                                            input_heatnode['pilot'] = p['db_id']
                                            break
                            elif input_heatnode['method'] == ProgramMethod.HEAT_RESULT:
                                for h in data['Heat']:
                                    if h['source_id'] == input_heatnode['seed_id']:
                                        input_heatnode['seed_heat_id'] = h['db_id']
                                        break

                            elif input_heatnode['method'] == ProgramMethod.CLASS_RESULT:
                                for c in data['RaceClass']:
                                    if c['source_id'] == input_heatnode['seed_id']:
                                        input_heatnode['seed_class_id'] = c['db_id']
                                        break

                            batch.append(input_heatnode)
                            break
                    break

        RHAPI.db.slot_alter_fast(batch)

    return True

def discover(*_args, **_kwargs):
    # returns array of exporters with default arguments, fields
    return [
        DataImporter(
            'json',
            'RotorHazard 4.0 JSON',
            import_json,
            None,
            [
                {
                    'id': 'reset_pilots',
                    'label': "Reset Pilots",
                    'fieldType': 'checkbox',
                    'value': False
                },
                {
                    'id': 'reset_formats',
                    'label': "Reset Formats",
                    'fieldType': 'checkbox',
                    'value': False
                },
                {
                    'id': 'reset_profiles',
                    'label': "Reset Profiles",
                    'fieldType': 'checkbox',
                    'value': False
                },
                {
                    'id': 'reset_classes',
                    'label': "Reset Classes and Race Data",
                    'fieldType': 'checkbox',
                    'value': False
                },

            ]
        ),
    ]
