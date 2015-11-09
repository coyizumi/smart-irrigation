from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
import ConfigParser
import MySQLdb


app = Flask(__name__)
api = Api(app)

config = ConfigParser.RawConfigParser()
config.read("config")

# Pull settings from the MySQL section of config file
sql_config = {
  'user': config.get('MySQL', 'user'),
  'passwd': config.get('MySQL', 'password'),
  'host': config.get('MySQL', 'host'),
  'db': config.get('MySQL', 'database'),
}

# Arguments will be field: the name of the field to pull (specify field multiple times to pull multiple fields)
# Start and end, the start and end dates. Results will be in the form of
# a list of all times and fields (in a dict) that fall between the start and end date
# Sample call: /get_field?field=temp&start=%222014-10-06_06:27:29%22&end=%222015-12-22_14:04:29%22
# Sample call (pulling multiple fields): /get_field?field=s1&field=s2&start=%222014-10-06_06:27:29%22&end=%222015-12-22_14:04:29%22
class GetField(Resource):
    def get(self):
        # Set up argument parser
        parser = reqparse.RequestParser()
        parser.add_argument('field', required=True, action='append')
        parser.add_argument('start', required=True)
        parser.add_argument('end', required=True)
        # Parse arguments
        args = parser.parse_args()
        # Form query using the received arguments
        query = ("SELECT time, {} FROM entry where time BETWEEN {} and {}".format(",".join(args['field']), args['start'], args['end']))
        # Print for debugging
        print query

        # Perform the query and store result
        result = performQuery (query)
        print result

        return result

def performQuery (query):
    # Connect to db
    conn = MySQLdb.connect(**sql_config)
    cursor = conn.cursor()
    # Perform query and fetch results
    cursor.execute(query)
    result = cursor.fetchall()
    # Make a list of the fields that were queried
    columns = [column[0] for column in cursor.description]
    results = []

    # Transform the results from a list of tuples to a list of dicts
    for row in result:
        results.append(dict(zip(columns, row)))

    # Transform any time values in the dicts from the weird MySQL format
    # into a usable string
    for row in results:
        # Eventually, change this to account for any TIMESTAMP specified in config
        if 'time' in row:
            row['time'] = row['time'].strftime('%Y-%m-%d %H:%M:%S')

    # Clean up and return
    cursor.close( )
    conn.close( )
    return results

##
## Actually setup the Api resource routing here
##
api.add_resource(GetField, '/get_field')


if __name__ == '__main__':
    app.run(debug=True)
