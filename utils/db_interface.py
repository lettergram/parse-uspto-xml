import os
import csv
import ast

# load the psycopg to connect to postgresql       
import psycopg2
import psycopg2.extras

class PGDBInterface:

    def __init__(self, check_environment=True,
                 config_file="../config/postgres.tsv",
                 set_remote=False, silent_logging=False):
        
        self.conn           = None
        self.cursor         = None
        self.set_remote     = set_remote
        self.silent_logging = silent_logging
        
        self.create_db_connection(check_environment, config_file)
        
        # Ensures immediate commits, not waiting for transactions
        self.conn.autocommit = True 


    def create_db_connection(self, check_environment=True,
                             config_file="../config/postgres.tsv"):
        """
        Attempt to create a postgresql database connection
        :param check_environment: Checks the environment variables for
                                  DATABASE_HOST, DATABASE_PORT, etc.
        :param config_file: The configuration file used as back up to 
                            the environment variables, or as primary if
                            check environment is not set.
        """
        
        remote = self.set_remote

        # Check if database parameters in environment
        params = {}
        if check_environment:
            if not self.silent_logging:
                print("\nChecking Environment Parameters for Database\n")
            if 'DATABASE_NAME' in os.environ:
                params['database'] = os.environ['DATABASE_NAME']
            else:
                if not self.silent_logging:
                    print("Environment variable DATABASE_NAME not set")
            if 'DATABASE_HOST' in os.environ:
                params['host'] = os.environ['DATABASE_HOST']
            else:
                if not self.silent_logging:
                    print("Environment variable DATABASE_HOST not set")
            if 'DATABASE_PORT' in os.environ:
                params['port'] = os.environ['DATABASE_PORT']
            else:
                if not self.silent_logging:
                    print("Environment variable DATABASE_PORT not set")
            if 'DATABASE_USER' in os.environ:
                params['user'] = os.environ['DATABASE_USER']
            else:
                if not self.silent_logging:
                    print("Environment variable DATABASE_USER not set")
            if 'DATABASE_PASS' in os.environ:
                params['password'] = os.environ['DATABASE_PASS']
            else:
                if not self.silent_logging:
                    print("Environment variable DATABASE_PASS not set")

        # If no environment parameters used and config file exists
        if not params and os.path.isfile(config_file):

            if not self.silent_logging:
                print("\nUsing Config File for Database\n")
            
            # Find the database parameters, remote and local databases     
            with open(config_file, 'r') as tsvfile:
                r = csv.reader(tsvfile, delimiter='\t')
                count = 0
                for row in r:
                    if remote and row[0] == "remote":
                        params = ast.literal_eval(row[1])
                    elif not remote and row[0] == "local":
                        params = ast.literal_eval(row[1])
        else:
            if not self.silent_logging:
                print("Using Environment Variables for Database")            

        # Try to connect to database    
        try:
            
            if remote:
                if not self.silent_logging:
                    print("Connecting to remote database")
                self.conn = psycopg2.connect(database=params["database"],
                                             user=params["user"],
                                             password=params["password"],
                                             host=params["host"],
                                             port=params["port"],
                                             sslmode='require')
            else:
                if not self.silent_logging:
                    print("Connecting to local database")
                self.conn = psycopg2.connect(database=params["database"],
                                             user=params["user"],
                                             password=params["password"],
                                             host=params["host"],
                                             port=params["port"])
        except Exception as err:
            print("I am unable to connect to the database.")
            print(err)
            exit()

        print("Connected to database")
        self.cursor = self.conn.cursor()
    
    def obtain_db_connection(self):
        return self.conn

    def obtain_db_cursor(self):
        return self.cursor

    def commit_to_db(self):
        # Make the changes to the database persistent=
        if not self.silent_logging:
            print("Committing to database")
        self.conn.commit()

    def close_db_connection(self):
        
        # Close communication with the database
        if not self.silent_logging:
            print("Closing cursor")        
        self.cursor.close()
        
        if not self.silent_logging:
            print("Closing connection")            
        self.conn.close()
        
        self.cursor  = None
        self.conn    = None
        
        print("Disconnected from database")
