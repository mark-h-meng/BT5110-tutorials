import re
import os
import csv
import logging
from sys import stdout

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT 
import os

logging.basicConfig(filename='file_processing.log', filemode='w', level=logging.DEBUG)

dbname='CC'
user='postgres'
password='admin'
host='localhost'

EXECUTE_QUERY = True
KEEP_LINE_BREAK = True

regex = re.compile(r'[\n\r\t]')
initialize_connecconnection_commandtion_command = "dbname='" + dbname + "' user='" + user + "' host='" + host + "' password='" + password + \
     "'" + " options='-c statement_timeout=30000'"

default_question_pattern = '/* Question '

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
            sid = file_name.split('.sql')[0]
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
# [Special for Proj 1] Q1.(d) we only show first 3 lines for each table populating
def extract_student_answers(submission_files, project_questions, csv_format = ['comment', 'grade'], 
    question_pattern = default_question_pattern, output_file = 'output.csv'):
    if submission_files is not None:
        student_id_lst, student_file_lst = extract_student_id(submission_files)
    print(str(len(student_id_lst)) + " students ID extracted from " + str(len(student_file_lst)) + " files")
    # match pattern is a list of Boolean variables to indicate whether the file
    #   reader has found a beginning pattern of new question
    match_pattern = False

    output_file = open(output_file, "w", newline='', encoding="UTF-8")
    #output_file = open(output_file, "w", newline='')
    # create the csv writer
    writer = csv.writer(output_file)

    header = ['student']
    for qn in project_questions:
        header.append(qn)
        if EXECUTE_QUERY:
            header.append('output')
        for col in csv_format:
            header.append(col)

    writer.writerow(header)

    total_num_files = len(student_file_lst)
    file_count = 1
    
    for index, item in enumerate(student_file_lst):
        student_row = [student_id_lst[index]]
        print("[" + "{:.2%}".format(file_count/total_num_files) + "] Reading submission: " + student_id_lst[index], end = "")

        input_file = open(item, 'r', encoding="utf8")
        reader_lines = input_file.readlines()

        line_count = 0
        question_index = -1 # Each submission file always starts with student's info
        solution_string = ''

        extra_comment = ''

        # Strips the newline character
        for line in reader_lines:
            line_count += 1

            if match_pattern:
                # increment question counting and reset match pattern
                match_pattern = False
                if question_index >= 0:
                    student_row.append(solution_string.strip())

                    if EXECUTE_QUERY:
                        # rows = psql_execute_query(solution_string.replace('\n', ' '), question="("+project_questions[question_index]+")")
                        rows = psql_execute_query(solution_string, question="("+project_questions[question_index]+")")
                        student_row.append(summarize_sql_output(rows)) 

                        extra_comment = check_semicolons(solution_string, extra_comment)
                        if question_index == 5 or question_index == 6:
                            extra_comment = check_aggregation_free(solution_string, extra_comment)

                    # Leave an empty cell for comments and/or grading                    
                    for col in csv_format:
                        student_row.append(extra_comment) 
                    
                    extra_comment = ''
                    solution_string = ''
                print('.', end = "")
                question_index += 1
                logging.debug("SOLUTION OF " + project_questions[question_index] + " IS SHOWN BELOW:")

            if line.startswith(question_pattern):
                # Start reading the solution for the next question
                match_pattern = True
            else:
                # Continue reading the solution for the current question if the question_index is not -1
                if len(line.strip()) > 0 and question_index >= 0:
                    
                    # Remove comments from line
                    comment_loc_start = line.find('/*')
                    if comment_loc_start >= 0:
                        comment_loc_end = line.find('*/')
                        line_without_comment = line[0:comment_loc_start] + line[comment_loc_end + 2:]
                        line = line_without_comment
                    
                    if line.find('--') >= 0:
                        line = ""

                    if KEEP_LINE_BREAK:
                        if len(line.strip()) == 0:
                            line = ""
                    else:
                        line = line.strip()
    
                    logging.info("Line{}: {}".format(line_count, line))

                    solution_string += line

        student_row.append(solution_string.strip())
        
        if EXECUTE_QUERY:
            rows = psql_execute_query(solution_string, question="("+project_questions[question_index]+")")
            student_row.append(summarize_sql_output(rows)) 
        
        extra_comment = check_semicolons(solution_string, extra_comment)
        if question_index == 5 or question_index == 6:
            extra_comment = check_aggregation_free(solution_string, extra_comment)

        for col in csv_format:
            student_row.append(extra_comment) 
        
        writer.writerow(student_row)
        
        print('.')
        file_count += 1
    output_file.close()

def psql_execute_query(query, question=""):
    try:     
        rows = []
        conn = psycopg2.connect(initialize_connecconnection_commandtion_command)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        try:
            cur.execute(query)
            conn.commit()
            
            rows.append(cur.fetchall())
        except psycopg2.Error as errorMsg:
            print(errorMsg, question, end="")        
            conn.rollback()
        #for index, row in enumerate(rows):
        #    print(len(row), "row(s) returned")
        return rows
    except Exception as error:
        print("Database query error: ", error, question, end="")
        print("Exception TYPE:", type(error), question, end="")

def summarize_sql_output(rows):
    if rows is None or len(rows) < 1:
        return "No output"
    output_summary = str(len(rows[0])) + ", " 
    if len(rows[0]) > 3:
        output_summary = output_summary + str(rows[0][:3])
    else:
        output_summary = output_summary + str(rows[0])
    return output_summary


def validate_sql_output(query_output_rows, num_rows, rows_checklist=[], sorted=False):
    comment = ''
    # Step 1: check the number of rows
    if num_rows != len(query_output_rows):
        comment += "Wrong number of rows (" + num_rows +" expected, but " + len(query_output_rows) + "obeserved).\n"
    
    # Step 2: spot-check/audit over the rows
    all_right = 1
    example_missing_row = ""
    for item in rows_checklist:
        if item not in query_output_rows:
            all_right *= 0
            example_missing_row = item
    if all_right != 1:
        comment += "Rows missing from the output (e.g.," + item + ").\n"

    # Step 3: check if the order of rows are correct (optional)
    if sorted:
        all_right = 1
        for index, item in enumerate(rows_checklist):
            if query_output_rows[index] != item:
                all_right *= 0
        if all_right != 1:
            comment += "Inconsistent of output (wrong order).\n"
    
    return comment

def generate_auditing_creteria():
    list_num_rows = [26, 21, 1301, 20816, 4, 16, 16, 7]
    list_rows_checklist = []
    list_sorted = []

    # Q1(a)
    list_sorted.append(False)
    list_rows_checklist.append([('136-28-0136',), ('148-29-1885',), 
        ('323-84-2652',), ('333-43-8426',), 
        ('702-03-0356',), ('759-92-7862',),
        ('844-31-6186',), ('846-33-7185',)])
    
    # Q1(b)
    list_sorted.append(False)
    list_rows_checklist.append([('Carleen', 'Tonkinson'), ('Cort', 'Coole'), 
        ('Brittany', 'Huggen'), ('Rowney', 'McSparran'), 
        ('Dukey', 'Malthus'), ('Baird', 'Menco')])

    # Q1(c)
    list_sorted.append(False)
    list_rows_checklist.append([('111-11-1111', 0), ('508-12-4770', 2), 
        ('734-49-4905', 2), ('356-78-0144', 2), 
        ('308-56-5739', 4), ('159-49-0391', 4)])
    
    # Q1(d)
    list_sorted.append(False)
    list_rows_checklist.append([('101-23-4003', 'diners-club-enroute', 0), 
        ('101-23-4003', 'diners-club-carte-blanche', 1), 
        ('101-23-4003', 'switch', 0), ('101-23-4003', 'visa', 0), 
        ('101-23-4003', 'maestro', 0), ('101-23-4003', 'laser', 0), 
        ('101-23-4003', 'instapayment', 0), ('101-23-4003', 'bankcard', 0), 
        ('101-23-4003', 'solo', 0), ('101-23-4003', 'mastercard', 0), 
        ('101-23-4003', 'china-unionpay', 1), ('101-23-4003', 'americanexpress', 0), 
        ('101-23-4003', 'visa-electron', 0), ('101-23-4003', 'diners-club-international', 0), 
        ('101-23-4003', 'diners-club-us-ca', 0), ('101-23-4003', 'jcb', 0), 
        ('899-12-5853', 'maestro', 0), ('899-12-5853', 'mastercard', 0), 
        ('899-12-5853', 'china-unionpay', 0), ('899-12-5853', 'laser', 0), 
        ('899-12-5853', 'visa-electron', 0), ('899-12-5853', 'instapayment', 0), 
        ('899-12-5853', 'bankcard', 0), ('899-12-5853', 'switch', 0), 
        ('899-12-5853', 'diners-club-enroute', 0), ('899-12-5853', 'jcb', 2), 
        ('899-12-5853', 'solo', 0), ('899-12-5853', 'diners-club-carte-blanche', 0), 
        ('899-12-5853', 'diners-club-us-ca', 0), ('899-12-5853', 'visa', 0), 
        ('899-12-5853', 'americanexpress', 1), ('899-12-5853', 'diners-club-international', 0)])
    
    # Q1(e)
    list_sorted.append(False)
    list_rows_checklist.append([('Indonesia', 850), ('Malaysia', 41), 
        ('Singapore', 300), ('Thailand', 109)])
    
    # Q1(f)
    list_sorted.append(False)
    list_rows_checklist.append([(1941,), (2196,), 
        (12254,), (13356,), 
        (27406,), (28078,)])

    # Q1(g)
    list_sorted.append(False)
    list_rows_checklist.append([(1941,), (2196,), 
        (12254,), (13356,), 
        (27406,), (28078,)])
    
    # Q1(h)
    list_sorted.append(False)
    list_rows_checklist.append([('50-9541874', 'Bartoletti-Wilderman'), 
        ('37-2421122', 'Torp-Vandervort'), 
        ('87-5899014', 'Nicolas, Olson and Krajcik')])

    return list_num_rows, list_rows_checklist, list_sorted


def check_aggregation_free(solution, comment=''):
    clue_str = ''
    if re.search('having ', solution, re.IGNORECASE):
        clue_str += ' HAVING '
    if re.search('group by ', solution, re.IGNORECASE):
        clue_str += ' GROUP-BY '
    '''
    if re.search(' sum', solution, re.IGNORECASE):
        clue_str += ' SUM '
    if re.search(' count', solution, re.IGNORECASE):
        clue_str += ' COUNT '
    if re.search(' avg', solution, re.IGNORECASE):
        clue_str += ' AVG '
    if re.search(' min', solution, re.IGNORECASE):
        clue_str += ' MIN '
    if re.search(' max', solution, re.IGNORECASE):
        clue_str += ' MAX '
    '''
    if len(clue_str) > 0:
        if len(comment) > 0:
            comment += '\n' 
        comment = 'Aggregation is used, CHECK CODE.'  
    return comment

def check_semicolons(solution, comment=''):
    if solution.find(';') < 0:
        if len(comment) > 0:
            comment += '\n' 
        comment = 'Missing semicolon, CHECK CODE.'  
    return comment

dirpath=('submission\\project2\\')
arr = retrieve_all_submission_files(dirpath)

project_one = ['1.a',  '1.b', '1.c',  '1.d', '1.e',  '1.f', '1.g', '1.h']
extract_student_answers(arr, 
    project_questions = project_one, 
    csv_format = ['comment', 'grade'], 
    output_file = 'output_p2.csv')