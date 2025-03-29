# import xbmc
import sqlite3

class Database:
    
    def log(self, message, error = ''):
        return # print(f'\n{message} {error}')
        
    def delete_table(self, filename,table_name):
        # if PathExists(filename):
            conn = sqlite3.connect(filename)
            cursor = conn.cursor()
            sql = f'DROP TABLE IF EXISTS {table_name};' 
            cursor.execute(sql)
            conn.commit()
            conn.close()
    
    def create_table(self, filename, table_name, _columns: tuple):
        try:
            db_connect = sqlite3.connect(filename)
            table = f'CREATE TABLE {table_name} {_columns};'
            # print('\n') 
            # print(table)
            cursor = db_connect.cursor()
            self.log('Successfully Connected to SQLite.')
            cursor.execute(table)
            db_connect.commit()
            self.log('SQLite table created.')
        except sqlite3.Error as e:
            self.log('Error while creating a sqlite table: ', e)
        finally:
               if db_connect:
                   db_connect.close()
                   self.log('SQLite connection is closed.')
    
    def get_placeholders(self,  _values: tuple):
        placeholders = []
        for x in _values:
            placeholders.append('?')
        return str(tuple(placeholders)).replace("'", "")

    def insert_into_db(self, db_file, table_name, columns: tuple, values: tuple):
       try:
           db_connect = sqlite3.connect(db_file)
           cursor = db_connect.cursor()
           self.log('Successfully Connected to SQLite.')
           placeholders = self.get_placeholders(values)
           # print('\n') 
           # print(placeholders)
           sqlite_insert_query = f'INSERT INTO {table_name} {columns} VALUES {placeholders}' # number of question marks must be equal to len(values)
           
           cursor.execute(sqlite_insert_query, values)
           db_connect.commit()
           self.log(f'Record inserted successfully into {table_name} table.')
           cursor.close()
       except sqlite3.Error as e:
           self.log('Failed to insert data into sqlite table: ', e)
       finally:
           if db_connect:
               db_connect.close()
               self.log('The SQLite connection is closed')

    def read_table(self, db_file, table_name):
       try:
           sqliteConnection = sqlite3.connect(db_file)
           cursor = sqliteConnection.cursor()
           # print('\n') 
           # print('Connected to SQLite')
           sqlite_select_query = f'SELECT * from {table_name}'
           cursor.execute(sqlite_select_query)
           record = cursor.fetchall()
           # print('\n') 
           # print("Total rows are:  ", len(record))
           cursor.close()
       
       except sqlite3.Error as e:
           self.log('Failed to read data from sqlite table: ', e)
       finally:
           if sqliteConnection:
               sqliteConnection.close()
               # print('\n') 
               # print('The SQLite connection is closed.')
       return record

    def search_db(self, db_file, table_name,  _id):
        for x in self.read_table(db_file, table_name):
            if _id in x:
                return x
        return False



