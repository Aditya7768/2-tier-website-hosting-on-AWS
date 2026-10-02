# import the JSON utility package
import json

# import the AWS SDK (for Python the package name is boto3)
import boto3
# import two packages to help us with dates and date formatting
from time import gmtime, strftime

# create a DynamoDB object using the AWS SDK
dynamodb = boto3.resource('dynamodb')
# use the DynamoDB object to select our table
table = dynamodb.Table('riskcal')

# define the handler function that the Lambda service will use as an entry point
def lambda_handler(event, context):

    # store the current time in a human readable format in a variable
    now = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())

    # API Gateway sends the data as a JSON string in event['body'];
    # the Lambda test console sends it directly in the event object
    if 'body' in event and event['body']:
        data = json.loads(event['body'])
    else:
        data = event

    # extract the values from the event object
    balance = float(data['balance'])
    riskPct = float(data['risk_pct'])
    stopPips = float(data['stop_pips'])
    price = float(data['price'])
    pair = str(data['pair']).upper()

    # a pip is 0.01 for JPY pairs and 0.0001 for all others
    if pair.endswith('JPY'):
        pipSize = 0.01
    else:
        pipSize = 0.0001

    # value of one pip for one standard lot (100,000 units), in the quote currency
    pipValue = pipSize * 100000

    # if USD is the base currency (USDJPY, USDCHF, USDCAD), convert the pip value to USD
    if not pair.endswith('USD'):
        pipValue = pipValue / price

    # how much money we are willing to lose on this trade
    riskAmount = balance * riskPct / 100

    # position size in standard lots
    lots = riskAmount / (stopPips * pipValue)

    # write the result and time to the DynamoDB table
    # (DynamoDB does not accept floats, so numbers are saved as strings)
    response = table.put_item(
        Item={
            'ID': str(round(lots, 2)),
            'LatestCalculationTime': now,
            'Pair': pair,
            'Balance': str(balance),
            'RiskPercent': str(riskPct),
            'StopPips': str(stopPips),
            'Price': str(price),
            'RiskAmount': str(round(riskAmount, 2))
        })

    # return a properly formatted JSON object (with CORS headers for the browser)
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'lots': round(lots, 2),
            'units': round(lots * 100000),
            'risk_amount': round(riskAmount, 2),
            'pip_value_per_lot': round(pipValue, 2)
        })
    }
