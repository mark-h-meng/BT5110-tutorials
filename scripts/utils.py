import os
import csv
import logging
from sys import stdout

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT 
import os

logging.basicConfig(filename='file_processing.log', filemode='w', level=logging.DEBUG)

dbname='BT5110'
user='postgres'
password='admin'
host='localhost'

initialize_connection_command = "dbname='" + dbname + "' user='" + user + "' host='" + host + "' password='" + password + "'"

default_question_pattern = ['/************',
                    '/*           ',
                    '/* Question ',
                    '/*           ', 
                    '/************']

# Given a list of files submitted by students, output the list of student IDs
def extract_student_id(filenames):
    if len(filenames) <= 0:
        return None
    sid_list = []
    file_list = []
    for filepath in filenames:
        file_dir, file_name = os.path.split(filepath)
        if 'answers(A' in file_name:
            startindex = file_name.find('answers(A') + 9
            sid = file_name[startindex - 1 : startindex + 8]
        elif 'answer(A' in file_name:
            startindex = file_name.find('answer(A') + 8
            sid = file_name[startindex - 1 : startindex + 8]
        else:
            sid = file_name
        sid_list.append(sid)
        file_list.append(filepath)
    
    return sid_list, file_list


# Retrieve all files for a specific project
def retrieve_all_submission_files(dirpath):
    files = os.listdir(dirpath)
    files_with_path = []
    for filename in files:
        if filename[-4:] == '.sql':
            full_path = os.path.join(dirpath, filename)
            files_with_path.append(full_path)
    return files_with_path


# Extract student's anwser for each questions and save in a CSV file
def extract_student_answers(submission_files, project_questions, csv_format = ['comment', 'grade'], 
    question_pattern = default_question_pattern, output_file = 'output.csv'):
    if submission_files is not None:
        student_id_lst, student_file_lst = extract_student_id(submission_files)
    print(str(len(student_id_lst)) + " students ID extracted from " + str(len(student_file_lst)) + " files")
    # match pattern is a list of Boolean variables to indicate whether the file
    #   reader has found a beginning pattern of new question
    match_pattern = [False] * len(question_pattern)

    output_file = open(output_file, "w", newline='', encoding="UTF-8")
    #output_file = open(output_file, "w", newline='')
    # create the csv writer
    writer = csv.writer(output_file)

    header = ['student']
    for qn in project_questions:
        header.append(qn)
        for col in csv_format:
            header.append(col)

    writer.writerow(header)
    for index, item in enumerate(student_file_lst):
        student_row = [student_id_lst[index]]

        input_file = open(item, 'r', encoding="utf8")
        reader_lines = input_file.readlines()

        line_count = 0
        pattern_index = 0
        question_index = -1
        solution_string = ''
        # Strips the newline character
        for line in reader_lines:
            line_count += 1
            line_utf = line.encode()

            if False not in match_pattern:
                # increment question counting and reset match pattern
                pattern_index = 0
                match_pattern = [False] * len(question_pattern)
                if question_index >= 0:
                    student_row.append(solution_string)

                    # Leave an empty cell for comments and/or grading                    
                    for col in csv_format:
                        student_row.append("") 

                    solution_string = ''
                question_index += 1
                logging.debug("SOLUTION OF " + project_questions[question_index] + " IS SHOWN BELOW:")

            if line.startswith(question_pattern[pattern_index]):
                match_pattern[pattern_index] = True
                pattern_index += 1
            else:
                if len(line.strip()) > 0 and question_index >= 0:
                    logging.info("Line{}: {}".format(line_count, line.strip()))
                    solution_string += line
            #print("Line{}: {}".format(line_count, match_pattern))
        
        student_row.append(solution_string)
        
        # Leave an empty cell for comments and/or grading                    
        for col in csv_format:
            student_row.append("") 
        
        writer.writerow(student_row)
    output_file.close()

# Extract student's anwser for each questions and save in a CSV file
def extract_student_answers_psql(submission_files, project_questions, csv_format = ['comment', 'grade'], 
    question_pattern = default_question_pattern, output_file = 'output.csv'):
    if submission_files is not None:
        student_id_lst, student_file_lst = extract_student_id(submission_files)
    print(str(len(student_id_lst)) + " students ID extracted from " + str(len(student_file_lst)) + " files")
    # match pattern is a list of Boolean variables to indicate whether the file
    #   reader has found a beginning pattern of new question
    match_pattern = [False] * len(question_pattern)

    output_file = open(output_file, "w", newline='', encoding="UTF-8")
    #output_file = open(output_file, "w", newline='')
    # create the csv writer
    writer = csv.writer(output_file)

    header = ['student']
    for qn in project_questions:
        header.append(qn)
        for col in csv_format:
            header.append(col)

    writer.writerow(header)
    for index, item in enumerate(student_file_lst):
        student_row = [student_id_lst[index]]

        input_file = open(item, 'r', encoding="utf8")
        reader_lines = input_file.readlines()

        line_count = 0
        pattern_index = 0
        question_index = -1
        solution_string = ''

        # psql_create_database(student_id_lst[index])

        # Strips the newline character
        for line in reader_lines:
            line_count += 1

            if False not in match_pattern:
                # increment question counting and reset match pattern
                pattern_index = 0
                match_pattern = [False] * len(question_pattern)
                if question_index >= 0:
                    student_row.append(solution_string)

                    # execution_outputss = psql_execute_query(database_name = student_id_lst[index], query = solution_string)

                    # Leave an empty cell for comments and/or grading                    
                    for col in csv_format:
                        student_row.append("") 

                    solution_string = ''
                question_index += 1
                logging.debug("SOLUTION OF " + project_questions[question_index] + " IS SHOWN BELOW:")

            if line.startswith(question_pattern[pattern_index]):
                match_pattern[pattern_index] = True
                pattern_index += 1
            else:
                if len(line.strip()) > 0 and question_index >= 0:
                    logging.info("Line{}: {}".format(line_count, line.strip()))
                    solution_string += line
            #print("Line{}: {}".format(line_count, match_pattern))
        
        student_row.append(solution_string)
        
        # Leave an empty cell for comments and/or grading                    
        for col in csv_format:
            student_row.append("") 

        writer.writerow(student_row)
        
        # (student_id_lst[index])

    output_file.close()

def psql_create_database(database_name):
    try:
        conn = psycopg2.connect(initialize_connection_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Use the psycopg2.sql module instead of string concatenation 
        # in order to avoid sql injection attacs.
        cur.execute(sql.SQL("CREATE DATABASE {};").format(
                sql.Identifier(database_name))
        )

    except Exception as error:
        print("Database creation error: ", error)
        print("Exception TYPE:", type(error))


def psql_execute_query(database_name, query):
    try:     
        rows = []
        connection_command = "dbname='" + database_name + "' user='" + user + "' host='" + host + "' password='" + password + "'"
        conn = psycopg2.connect(connection_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        for line in query.split(';'):    
            try:
                line = line.replace('\n','')
                line = line.replace('\t','')
                cur.execute(f'{line}')
                conn.commit()
            
                rows.append(cur.fetchall())
            except psycopg2.Error as errorMsg:
                print(errorMsg)        
                conn.rollback()
        for index, row in enumerate(rows):
            print(index, "\t", row)
        return rows
    except Exception as error:
        print("Database query error: ", error)
        print("Exception TYPE:", type(error))


def psql_drop_database(database_name):
    try:
        conn = psycopg2.connect(initialize_connection_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Use the psycopg2.sql module instead of string concatenation 
        # in order to avoid sql injection attacs.
        cur.execute(sql.SQL("DROP DATABASE {};").format(
                sql.Identifier(database_name))
        )

    except Exception as error:
        print("Database creation error: ", error) 
        print("Exception TYPE:", type(error))


dirpath=('submission\\project1\\')
arr = retrieve_all_submission_files(dirpath)

project_one = ['1.a',  '1.b', '1.c',  '1.d', '1.e',  '2']
extract_student_answers(arr, 
    project_questions = project_one, 
    csv_format = ['comment', 'grade'], 
    output_file = 'output.csv')