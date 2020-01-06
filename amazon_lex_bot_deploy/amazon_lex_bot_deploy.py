import json
import boto3
import logging
import zipfile
import ntpath
import io
import re
import botocore
import os
from botocore.vendored import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEFAULT_REGION = 'us-east-1'

logger = logging.getLogger(__name__)

LATEST_ALIAS = '$LATEST'


@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1.5),
       retry=retry_if_exception_type(boto3.client('lex-models', region_name='us-east-1').exceptions.ConflictException))
def retry_function(f, **kwargs):
    """
    retries the function passed in
    :param f: function name
    :param kwargs: parameters for the function
    :return: function result
    """
    if retry_function.retry.statistics['attempt_number'] > 1:
        logger.warning("Got ConflictException. More than 1 attempt for: {}, {}, {}"
                       .format(f, retry_function.retry.statistics, kwargs))
    return f(**kwargs)


@retry(stop=stop_after_attempt(8), wait=wait_exponential(multiplier=1), retry=retry_if_exception_type(ValueError))
def wait_async(f, status_name, status_values, failed_statuses=None, **kwargs):
    """
    wait till function is not in status_values any more
    you can change the params like this: wait_async.retry_with(stop=stop_after_attempt(4))()
    :param f: function to call to receive status
    :param status_name: attribute in response to check
    :param status_values: will wait as long as status is in status_values
    :param failed_statuses: raises Exception when status is in failed_statuses
    :param kwargs: any function parameter
    :return: response or Exception in case of error or status in failed_statuses
    """

    if failed_statuses is None:
        failed_statuses = []
    try:
        wait_response = f(**kwargs)
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(e)
        raise e

    if wait_response[status_name] in status_values:
        logger.info("Waiting. status_name: '{}' still in '{}', waiting to exit status '{}'."
                    .format(status_name, wait_response[status_name], status_values))
        raise ValueError("Waiting. status_name: '{}' still in '{}', waiting to exit status '{}'."
                         .format(status_name, wait_response[status_name], status_values))

    if wait_response[status_name] in failed_statuses:
        logger.error("failed, no need to wait longer. response: {}\n".format(wait_response))
        raise Exception("wait_response[status_name]: {} in failed_statuses: {}"
                        .format(wait_response[status_name], failed_statuses))

    return wait_response


def get_lambda_endpoints(full_schema):
    """
    returns a unique list of lambda endpoints from the Lex Schema
    :param full_schema:
    :return:
    """
    lambda_endpoints = set()
    for intent in full_schema['resource']['intents']:
        if 'fulfillmentActivity' in intent and 'codeHook' in intent['fulfillmentActivity']:
            lambda_endpoints.add(intent['fulfillmentActivity']['codeHook']['uri'])
        if 'dialogCodeHook' in intent:
            lambda_endpoints.add(intent['dialogCodeHook']['uri'])
    return lambda_endpoints


def create_lambda_permissions(lex_client, lambda_endpoints, region, bot_name):
    """
    creates permissions for Lex to call the defined Lambda function
    :param lex_client: boto3 lex client
    :param lambda_endpoints: endpoint arns
    :param region: region name
    :param bot_name: bot name
    :return: None, Exception when failure
    """
    try:
        lambda_client = setup_boto3_client(region, boto3_client='lambda')

        source_account_id = setup_boto3_client(region, boto3_client='sts').get_caller_identity()["Account"]

        for lambda_function in lambda_endpoints:
            try:
                lambda_client.add_permission(
                    FunctionName=lambda_function,
                    StatementId="{}-intents".format(bot_name),
                    Action="lambda:invokeFunction",
                    Principal="lex.amazonaws.com",
                    SourceArn="arn:aws:lex:{}:{}:intent:*".format(lex_client.meta.region_name, source_account_id)
                )
                logger.info("created permission for Lex bot: {} to call Lambda function: {}"
                            .format(bot_name, lambda_function))

            except lambda_client.exceptions.ResourceConflictException as rce:
                if re.match(".*The statement id .* provided already exists.*", str(rce)):
                    logger.debug("permission for Lex bot {} to call Lambda: {} exists."
                                 .format(bot_name, lambda_function))
                pass
    except Exception as e:
        logger.error('lambda permission error: {}'.format(e))


def lex_deploy(lex_schema_file=None, lex_alias=LATEST_ALIAS, lambda_endpoint=None, region=None, log_level='INFO',
               example=None):
    """
    deploys Amazon Lex schema file to either the $LATEST or a specific alias.
    :param lex_schema_file: location of lex schema file. Either example or lex_schema_file have to be set
    :param lex_alias: alias to deploy to, default is $LATEST
    :param lambda_endpoint: Lambda endpoint ARN. Will replace existing endpoints in Lambda schema
    :param region: AWS region to deploy to. default is taken from environment configuration or if nothing is set falls back to 'us-east-1'
    :param log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    :param example: one of "BookTrip", "OrderFlowers", "ScheduleAppointment". Either example or lex_schema_file have to be set
    :return: None if success
    """

    if example:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        lex_schema_file = os.path.join(SCRIPT_DIR, "examples/{}_Export.json".format(example))

    logger.setLevel(log_level)
    lex_client = setup_boto3_client(region)

    with open(lex_schema_file) as lex_schema_file_input:
        full_schema = json.load(lex_schema_file_input)
        schema_resource = full_schema['resource']
        voice_id = schema_resource['voiceId']
        bot_ttl = schema_resource['idleSessionTTLInSeconds']
        bot_name = schema_resource['name']
        child_directed = schema_resource['childDirected']

        logger.debug("voice_id: {}".format(voice_id))

        # replace existing Lambda endpoints with new one
        if lambda_endpoint:
            for intent in full_schema['resource']['intents']:
                if 'fulfillmentActivity' in intent and 'codeHook' in intent['fulfillmentActivity']:
                    logger.info(
                        "changing {} to {}".format(intent['fulfillmentActivity']['codeHook']['uri'],
                                                   lambda_endpoint))
                    intent['fulfillmentActivity']['codeHook']['uri'] = lambda_endpoint
                if 'dialogCodeHook' in intent:
                    logger.info("changing {} to {}".format(intent['dialogCodeHook']['uri'], lambda_endpoint))
                    intent['dialogCodeHook']['uri'] = lambda_endpoint
                    has_lambda_endpoints = True

        # check if Lex has permission to call Lambda, if not add the permissions
        lambda_endpoints = get_lambda_endpoints(full_schema)
        if lambda_endpoints:
            create_lambda_permissions(lex_client, lambda_endpoints, bot_name=bot_name, region=region)

        buff = io.BytesIO()

        zipfile_ob = zipfile.ZipFile(buff, mode='w')
        zipfile_ob.writestr(ntpath.basename(lex_schema_file), json.dumps(full_schema))

        buff.seek(0)

        try:
            start_import_response = lex_client.start_import(
                payload=buff.read(),
                resourceType='BOT',
                mergeStrategy='OVERWRITE_LATEST'
            )
        except botocore.exceptions.EndpointConnectionError as ece:
            logger.error(ece)
            logger.error("Maybe Amazon Lex is not supported in region defined. Check https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/")
            raise ece

        logger.debug("start_import_response: {}".format(start_import_response))

        import_id = start_import_response['importId']
        wait_async(lex_client.get_import, 'importStatus', ["IN_PROGRESS"], ["FAILED"], importId=import_id)

        bot_intents = []
        for intent in schema_resource['intents']:
            intent_name = intent['name']
            get_intent_response = lex_client.get_intent(
                name=intent_name,
                version=LATEST_ALIAS
            )
            logger.debug("{}, {}".format(intent_name, get_intent_response['checksum']))

            create_intent_version_response = retry_function(lex_client.create_intent_version, name=intent_name,
                                                            checksum=get_intent_response['checksum'])
            bot_intents.append({
                'intentName': intent_name,
                'intentVersion': create_intent_version_response['version']
            })

            logger.debug(create_intent_version_response)

        logger.info("deployed all intents")

        get_bot_response = lex_client.get_bot(
            name=bot_name,
            versionOrAlias=LATEST_ALIAS
        )
        logger.debug("STATUS: {}".format(get_bot_response['status']))

        wait_async(lex_client.get_bot, 'status', ['BUILDING'], ["FAILED"], name=bot_name, versionOrAlias=LATEST_ALIAS)

        put_bot_response = retry_function(lex_client.put_bot,
                                          name=bot_name,
                                          checksum=get_bot_response['checksum'],
                                          childDirected=child_directed,
                                          locale=schema_resource['locale'],
                                          abortStatement=schema_resource['abortStatement'],
                                          clarificationPrompt=schema_resource['clarificationPrompt'],
                                          intents=bot_intents,
                                          processBehavior='BUILD',
                                          voiceId=voice_id,
                                          idleSessionTTLInSeconds=bot_ttl
                                          )
        logger.debug("put_bot_response: %s", put_bot_response)

        response = wait_async(lex_client.get_bot, 'status', ['BUILDING', 'NOT_BUILT', 'READY_BASIC_TESTING'],
                              ["FAILED"], name=bot_name, versionOrAlias=LATEST_ALIAS)

        create_bot_version_response = retry_function(lex_client.create_bot_version,
                                                     name=bot_name,
                                                     checksum=response['checksum']
                                                     )

        new_version = create_bot_version_response['version']

        logger.debug("create_bot_version_response: {}".format(create_bot_version_response))

        if lex_alias == LATEST_ALIAS:
            logger.debug("deployed to alias: %s, no specific alias given", lex_alias)
            wait_response = wait_async(lex_client.get_bot, 'status', ['BUILDING', 'NOT_BUILT', 'READY_BASIC_TESTING'],
                                       ["FAILED"], name=bot_name, versionOrAlias=LATEST_ALIAS)

            logger.info("success. bot_status: {} for alias: {}".format(wait_response['status'], LATEST_ALIAS))

        else:
            logger.debug("deploying to alias: %s with version: %s.", lex_alias, new_version)
            try:
                # check if alias exists, need the checksum if updating
                bot_alias = lex_client.get_bot_alias(
                    name=lex_alias,
                    botName=bot_name
                )
                checksum = bot_alias['checksum']
                old_version = bot_alias['botVersion']

                if new_version != old_version:
                    logger.debug("new version: {} for existing alias: {} and version: '{}'"
                                 .format(new_version, lex_alias, old_version))
                    put_bot_alias_response = retry_function(lex_client.put_bot_alias,
                                                            name=lex_alias,
                                                            description='latest test',
                                                            botVersion=new_version,
                                                            botName=bot_name,
                                                            checksum=checksum
                                                            )
                    logger.debug("put_bot_alias_response : {}".format(put_bot_alias_response))

                    # wait for new version
                    wait_async(lex_client.get_bot, 'version', [old_version],
                               name=bot_name, versionOrAlias=lex_alias)
                    wait_response = wait_async(lex_client.get_bot, 'status',
                                               ['BUILDING', 'NOT_BUILT', 'READY_BASIC_TESTING'],
                                               ["FAILED"], name=bot_name, versionOrAlias=lex_alias)
                    logger.info("success. bot_status: {} for alias: {}".format(wait_response['status'], lex_alias))
                else:
                    logger.info('No change for bot. old version == new version ({} == {})'
                                .format(old_version, new_version))

            except lex_client.exceptions.NotFoundException:
                # alias not found, create new alias
                logger.debug("create new alias: '{}'.".format(lex_alias))
                put_bot_alias_response = retry_function(lex_client.put_bot_alias,
                                                        name=lex_alias,
                                                        description='latest test',
                                                        botVersion=new_version,
                                                        botName=bot_name
                                                        )

                logger.debug("put_bot_alias_response : {}".format(put_bot_alias_response))


def setup_boto3_client(region, boto3_client='lex-models'):
    try:
        lex_client = boto3.client(boto3_client) \
            if not region \
            else boto3.client(boto3_client, region_name=region)
    except botocore.exceptions.NoRegionError:
        logger.warning("no region defined or configured, going to default to: {}".format(DEFAULT_REGION))
        lex_client = boto3.client(boto3_client, region_name=DEFAULT_REGION)
    except ValueError as e:
        logger.warning("ValueError: {}. Going to default to default region: {}".format(e, DEFAULT_REGION))
        lex_client = boto3.client(boto3_client, region_name=DEFAULT_REGION)
    return lex_client


def lex_export_bot(name, version='1', region='us-east-1', log_level='INFO'):
    """
    return json string of current Lex bot definition
    :param name: Lex Bot name
    :param region: defaults to us-east-1
    :param log_level
    :param version: version to export, has to be numerical. Default is 1
    :return: None, Exception in case of failure
    """
    try:
        logger.setLevel(log_level)
        lex_client = setup_boto3_client(region=region)
        get_export_result = wait_async(f=lex_client.get_export,
                                       status_name='exportStatus',
                                       status_values=['IN_PROGRESS'],
                                       failed_statuses=['FAILED'],
                                       name=name,
                                       version=version,
                                       resourceType='BOT',
                                       exportType='LEX')
        download = requests.get(get_export_result['url'])

        buff = io.BytesIO(download.content)

        zipfile_ob = zipfile.ZipFile(buff)
        for zip_member in zipfile_ob.filelist:
            output_location = zipfile_ob.extract(member=zip_member)
            logger.info("Extracted {} to {}.".format(zip_member.filename, output_location))

    except Exception as e:
        logger.error("{}".format(e))
        raise e
