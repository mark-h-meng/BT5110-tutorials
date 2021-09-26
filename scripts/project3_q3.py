import re
import os, sys
import csv
import logging
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT 
import os

dbname='project3'
user='postgres'
password='admin'
host='localhost'

json_filepath = 'question3.json'

initialize_connection_command = "dbname='" + dbname + "' user='" + user + "' host='" + host + "' password='" + password + "'" 

long_query_list = ['A0041688X', 'A0119430N', 'A0179033E (LATE)',
                    'A0218877L', 'A0218915Y', 
                    'A0231857Y', 'A0231863E', 'A0231872E', 
                    'A0231902R', 'A0231906J', 'A0231907H', 
                    'A0231909A','A0231921N', 'A0232004A', 'A0232013A']


def read_json_from_file(filename):
    with open(filename) as f:
        data = json.load(f)
        # {"name": "A0123456B", "answers": ["SELECT ...;", "SELECT ...;"]}
    return data

def create_benchmark_dict(answer_dict, range=None):
    benchmark_dict = {}
    query_dict = {}
    if range is None:
        range = [0, len(answer_dict) - 1]
    print(range[1] - range[0], "answers will be executed...")
    for index,key in enumerate(answer_dict):
        if index >= range[0] and index < range[1]:
            benchmark = [-1] * len(answer_dict[key])
            benchmark_dict[key] = benchmark
            query_dict[key] = answer_dict[key]
    return query_dict, benchmark_dict

def execute_query(query, timeout=None):
    try:     
        rows = []
        if timeout:
            connect_command = initialize_connection_command + " options='-c statement_timeout=" + str(timeout) + "'"
        else:
            connect_command = initialize_connection_command 
        conn = psycopg2.connect(connect_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        try:
            cur.execute(query)
            conn.commit()
            
            rows.append(cur.fetchall())
        except psycopg2.Error as errorMsg:
            print(errorMsg, end="")        
            conn.rollback()
        return rows
    except Exception as error:
        print("Database query error: ", error, end="")
        print("Exception TYPE:", type(error), end="")

if __name__ == "__main__":
    student_answer_dict = read_json_from_file(json_filepath)
    # query_dict, benchmark_dict = create_benchmark_dict(student_answer_dict, [0,3])
    query_dict, benchmark_dict = create_benchmark_dict(student_answer_dict, [0, len(student_answer_dict)])
    
    output_dict = {}

    # for index,key in enumerate(query_dict):
    for index,key in enumerate(long_query_list): # The long_query_list is composed by a list of student IDs
        sid = key
        queries = query_dict[sid]
        outputs = []
        benchmarks = []
        for query in queries:
            print("[" + "{:.2%}".format((index+1)/len(query_dict)) + "]", end="")
            print(key, end="\t")
            # output_rows = execute_query(query, timeout=300000)
            output_rows = execute_query(query)
            if len(output_rows) > 0:
                outputs.append(output_rows)    
                print(output_rows, end="\t")
            
                benchmark_query = "SELECT test('" + query + "', 1);"
                # benchmark_rows = execute_query(benchmark_query, timeout=360000)
                benchmark_rows = execute_query(benchmark_query)
                benchmarks.append(benchmark_rows)
                print(benchmark_rows)
            
            else:
                outputs.append("")
                benchmarks.append("")
            
        output_dict[sid] = outputs
        benchmark_dict[sid] = benchmarks

    output_file = 'output_p3_3.csv'

    output_file = open(output_file, "w", newline='', encoding="UTF-8")
    # create the csv writer
    writer = csv.writer(output_file)
        
    writer.writerow(['student', 'answer', 'output', 'planning time', 'execution time'])
    for index2,key2 in enumerate(query_dict):
        for index3,item in enumerate(query_dict[key2]):
            if index3 == 0:
                row = [key2, item]
            else:
                row = [key2 + "(" + str(index3 + 1) + ")", item]
            row.append(output_dict[key2][index3])
            if len(benchmark_dict[key2][index3]) > 0:
                time_elapsed = sum(benchmark_dict[key2][index3], [])[0][0].split(":")
                row.append(time_elapsed[0])
                row.append(time_elapsed[1])
            else:
                row.append("TIMEOUT")
                row.append("TIMEOUT")
            writer.writerow(row)
    output_file.close()
    print("Task complished.")